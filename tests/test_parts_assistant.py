"""Local browser actions keep source-bound plans, safe inputs and private routes."""
from __future__ import annotations

import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from tests.support import reference_root
from tools.hwrepo.contract_coach import NetlistRunner, project_context
from tools.hwrepo.evidence import digest
from tools.hwrepo.models import (
    AutoCadItem,
    AutoCadReport,
    DigiKeyHandoffPayload,
    DigiKeyHandoffReply,
    PartCadComponent,
    PartPickerItem,
    PartPickerReport,
    PartSelectionAssignment,
    PartSelectionMap,
    PartSelectionReport,
    PurchasingLine,
    PurchasingPlan,
    PurchasingPreferences,
    PurchasingReport,
)
from tools.hwrepo.parts_assistant import Assistant, Form, create_server, render_html
from tools.hwrepo.parts_workflow import input_hashes


class FormTests(unittest.TestCase):
    def test_form_rejects_duplicate_unknown_and_invalid_quantities(self) -> None:
        with self.assertRaisesRegex(ValueError, "more than once"):
            Form.decode(b"boards=1&boards=2")
        for body in (b"boards=1", b"boards=1&spare_percent=0&spare_minimum=0&path=x",
                     b"boards=-1&spare_percent=0&spare_minimum=0",
                     b"boards=0&spare_percent=0&spare_minimum=0",
                     b"boards=1&spare_percent=101&spare_minimum=0"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                Form.decode(body).quantities()
        with self.assertRaises(ValueError):
            Form.decode(b"path=/private/secret").assignments()
        with self.assertRaises(ValueError):
            Form.decode(b"part...%2FR1=identity").assignments()
        with self.assertRaises(ValueError):
            Form.decode(b"plan=anything").empty()

    def test_form_converts_to_immutable_typed_values(self) -> None:
        self.assertEqual(Form.decode(b"part.R1=resistor-1k").assignments(),
                         (PartSelectionAssignment(reference="R1", part_id="resistor-1k"),))
        self.assertEqual(Form.decode(b"boards=4&spare_percent=10&spare_minimum=2").quantities(),
                         PurchasingPreferences(boards=4, spare_percent=10, spare_minimum=2))

    def test_page_has_no_source_html_injection_or_download_json_workflow(self) -> None:
        html = render_html('board<script>alert(1)</script>', PurchasingPreferences(), "nonce-safe")
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('board&lt;script&gt;', html)
        self.assertNotIn('innerHTML', html)
        self.assertNotIn('Download selection', html)
        self.assertIn("element('pre',report.diff)", html)
        self.assertIn("$('scan').click()", html)
        self.assertIn('Add matched models', html)
        self.assertIn('filter(issue=>!shownIssues.has(issue))', html)
        self.assertIn('CAD matching checks pads and preserves library model settings', html)
        self.assertNotIn('confirms its library alignment', html)
        self.assertIn("element('button','Send BOM to DigiKey')", html)
        self.assertIn("action('digikey','handoff-status'", html)
        self.assertIn('No API key is needed', html)
        self.assertIn("link.rel='noopener noreferrer'", html)
        self.assertIn("['boards','spare_percent','spare_minimum'].forEach", html)
        self.assertIn('clearOrderView();', html)
        self.assertIn('new URLSearchParams({review:report.receipt_dir})', html)


class AssistantHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="parts-assistant-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "source"
        shutil.copytree(reference_root(), self.root, ignore=shutil.ignore_patterns(".git"))
        self.server = create_server(self.root, "controller")
        self.addCleanup(self.server.server_close)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        self.thread.start()
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.shutdown)
        self.state = self.server.assistant
        self.base = "/" + self.state.token + "/"

    def request(self, method: str, action: str = "", body: str = "", *,
                origin: str | None = "auto", host: str | None = None,
                path: str | None = None, content_type: str = "application/x-www-form-urlencoded"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Content-Type": content_type}
        if origin is not None:
            headers["Origin"] = self.server.origin if origin == "auto" else origin
        if host is not None:
            headers["Host"] = host
        connection.request(method, path or self.base + action, body, headers)
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result

    def test_loopback_page_is_private_and_sets_browser_boundaries(self) -> None:
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, content = self.request("GET")
        self.assertEqual(status, 200)
        self.assertIn(b"Finish your board", content)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn("script-src 'nonce-", headers["Content-Security-Policy"])
        self.assertEqual(self.request("GET", path="/wrong-token/")[0], 404)
        self.assertEqual(self.request("GET", host="attacker.invalid")[0], 403)
        self.assertEqual(self.request("GET", "../../catalog/parts.json")[0], 404)
        self.assertEqual(self.request("GET", "download/report.json")[0], 404)

    def test_cross_origin_and_non_form_writes_are_rejected_before_backend(self) -> None:
        with patch.object(Assistant, "execute") as execute:
            self.assertEqual(self.request("POST", "scan", origin=None)[0], 403)
            self.assertEqual(self.request("POST", "scan", origin="https://attacker.invalid")[0], 403)
            self.assertEqual(self.request("POST", "scan", content_type="application/json")[0], 415)
            self.assertEqual(self.request("POST", "scan", host="attacker.invalid")[0], 403)
            self.assertEqual(self.request("POST", "scan", path="/wrong-token/scan")[0], 404)
            self.assertEqual(self.request("POST", "scan", body="x=" + "a" * 65536)[0], 413)
            execute.assert_not_called()

    def test_busy_action_refuses_a_second_write(self) -> None:
        self.state.lock.acquire()
        try:
            with patch.object(Assistant, "execute") as execute:
                self.assertEqual(self.request("POST", "scan")[0], 409)
                execute.assert_not_called()
        finally:
            self.state.lock.release()

    def test_cad_scan_and_apply_use_only_the_server_held_plan(self) -> None:
        plan_path = self.root / "build/cad-plan.json"
        report = AutoCadReport(project_id="controller", status="PLAN", plan_path=str(plan_path),
            receipt_directory=str(self.root / "build"), files=("examples/projects/controller/kicad/model.step",),
            items=(AutoCadItem(reference="R1", footprint="Device:R", status="READY", detail="Matched pair"),))
        applied = report.model_copy(update={"status": "APPLIED"})
        with patch("tools.hwrepo.auto_cad.plan", return_value=report) as planning:
            status, _, body = self.request("POST", "scan")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["plan_path"], str(plan_path))
        planning.assert_called_once()
        with patch("tools.hwrepo.auto_cad.apply", return_value=applied) as apply:
            self.assertEqual(self.request("POST", "apply", "path=/private/secret")[0], 400)
            apply.assert_not_called()
            status, _, _ = self.request("POST", "apply")
        self.assertEqual(status, 200)
        self.assertEqual(apply.call_args.args[2], plan_path)
        self.assertIsNone(self.state.cad_plan)
        self.assertEqual(self.request("POST", "apply")[0], 400)

    def test_partial_cad_review_still_has_exact_diff_and_per_reference_details(self) -> None:
        report = AutoCadReport(project_id="controller", status="PLAN", plan_path="build/plan.json",
            receipt_directory="build/review", diff='- old\n+ <script>untrusted</script>\n',
            items=(AutoCadItem(reference="D1", footprint="LED:Custom", status="NEEDS_REVIEW",
                               detail="Pad spacing differs from the source footprint"),))
        with patch.object(Assistant, "scan", return_value=report):
            status, _, body = self.request("POST", "scan")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["items"][0]["status"], "NEEDS_REVIEW")
        self.assertEqual(json.loads(body)["diff"], report.diff)

    def test_picker_selection_cannot_submit_unoffered_identity_or_source_hashes(self) -> None:
        component = PartCadComponent(reference="R1", value="1k", footprint="Device:R", symbol_id="Device:R",
                                     source_path="examples/projects/controller/kicad/controller.kicad_sch", uuid="uuid")
        self.state.picker = PartPickerReport(project_id="controller", status="READY", receipt_dir="build/picker",
            items=(PartPickerItem(component=component, choice_ids=("resistor-1k",)),),
            selection_template=PartSelectionMap(project_id="controller", preconditions={"catalog/parts.json": "1" * 64}))
        locked = self.root / "build/locked.json"
        report = PartSelectionReport(project_id="controller", status="PLAN", receipt_dir="build/review", locked_map=str(locked))
        with patch("tools.hwrepo.parts_assistant.selection", return_value=report) as selecting:
            self.assertEqual(self.request("POST", "select", "part.R1=unoffered")[0], 400)
            self.assertEqual(self.request("POST", "select", "part.R1=resistor-1k&preconditions=fake")[0], 400)
            selecting.assert_not_called()
            status, _, _ = self.request("POST", "select", "part.R1=resistor-1k")
            spec_path = selecting.call_args.args[2]
        self.assertEqual(status, 200)
        spec = PartSelectionMap.model_validate_json(spec_path.read_text())
        self.assertEqual(spec.preconditions, {"catalog/parts.json": "1" * 64})
        self.assertEqual(self.state.selection_plan, locked)
        with patch("tools.hwrepo.parts_assistant.selection", return_value=report) as applying:
            self.assertEqual(self.request("POST", "apply-selection")[0], 200)
        self.assertEqual(applying.call_args.args[2], locked)
        self.assertTrue(applying.call_args.kwargs["apply"])
        self.assertIsNone(self.state.selection_plan)

    def test_order_download_cannot_leak_other_files_and_rejects_stale_sources(self) -> None:
        receipt = self.root / "build/order"
        receipt.mkdir(parents=True)
        csv = receipt / "bom.csv"
        csv.write_text("Reference,Quantity\nR1,2\n", encoding="utf-8")
        _, _, source_hashes = project_context(self.root, "controller")
        report = PurchasingReport(project_id="controller", status="NEEDS_PARTS", receipt_dir=str(receipt),
            source_hashes=source_hashes, input_hashes=input_hashes(self.root, "controller", None), artifacts=("bom.csv",))
        self.state.order = report
        self.state.downloads["bom.csv"] = digest(csv)
        status, headers, content = self.request("GET", "download/bom.csv")
        self.assertEqual(status, 200)
        self.assertIn('filename="bom.csv"', headers["Content-Disposition"])
        self.assertEqual(content, csv.read_bytes())
        self.assertEqual(self.request("GET", "download/digikey.csv")[0], 409)
        self.assertEqual(self.request("GET", "download/../../catalog/parts.json")[0], 404)
        manifest = self.root / "examples/projects/controller/project.json"
        manifest.write_text(manifest.read_text() + "\n")
        self.assertEqual(self.request("GET", "download/bom.csv")[0], 409)
        self.assertIsNone(self.state.order)

    def test_tampered_download_is_rejected(self) -> None:
        receipt = self.root / "build/order"
        receipt.mkdir(parents=True)
        csv = receipt / "bom.csv"
        csv.write_text("original", encoding="utf-8")
        _, _, source_hashes = project_context(self.root, "controller")
        self.state.order = PurchasingReport(project_id="controller", status="NEEDS_PARTS", receipt_dir=str(receipt),
            source_hashes=source_hashes, input_hashes=input_hashes(self.root, "controller", None), artifacts=("bom.csv",))
        self.state.downloads["bom.csv"] = digest(csv)
        csv.write_text("changed", encoding="utf-8")
        self.assertEqual(self.request("GET", "download/bom.csv")[0], 409)

    def ready_order(self) -> PurchasingReport:
        receipt = self.root / "build/order"
        receipt.mkdir(parents=True, exist_ok=True)
        csv = receipt / "digikey.csv"
        csv.write_text("PartNumber,Quantity,CustomerReference\nRC0603FR-071KL,8,RES-1\n", encoding="utf-8")
        _, _, source_hashes = project_context(self.root, "controller")
        plan = PurchasingPlan(status="READY_FOR_ORDER_REVIEW",
            preferences=PurchasingPreferences(boards=3), components=(), findings=(),
            lines=(PurchasingLine(part_id="RES-1", revision="A", manufacturer="Yageo",
                mpn="RC0603FR-071KL", footprint="Resistor_SMD:R_0603_1608Metric", references=("R1", "R2"),
                per_board=2, required=6, spares=2, quantity=8, order_number="RC0603FR-071KL",
                order_number_kind="MPN", search_url="https://www.digikey.com/en/products"),))
        report = PurchasingReport(project_id="controller", status="READY_FOR_ORDER_REVIEW",
            receipt_dir=str(receipt), source_hashes=source_hashes,
            input_hashes=input_hashes(self.root, "controller", None), plan=plan, artifacts=("digikey.csv",))
        self.state.order = report
        self.state.downloads["digikey.csv"] = digest(csv)
        return report

    def handoff(self, review: str | None = None):
        return self.request("POST", "digikey", urlencode({"review": review or str(self.root / "build/order")}))

    def test_handoff_requires_ready_server_plan_and_exact_review_field(self) -> None:
        with patch("tools.hwrepo.digikey_handoff.send") as send:
            status, _, body = self.handoff()
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["status"], "BLOCKED")
            report = self.ready_order()
            for body in ("", "review=", "review=%20", "quantity=999&part=arbitrary", "review=old&quantity=999"):
                self.assertEqual(self.request("POST", "digikey", body)[0], 400)
            self.state.order = report.model_copy(update={"status": "NEEDS_PARTS"})
            self.assertEqual(json.loads(self.handoff()[2])["status"], "BLOCKED")
            self.state.order = report.model_copy(update={"plan": None})
            self.assertEqual(json.loads(self.handoff()[2])["status"], "BLOCKED")
            send.assert_not_called()

    def test_handoff_submits_server_order_once_and_caches_review_link(self) -> None:
        self.ready_order()
        reply = DigiKeyHandoffReply(single_use_url="https://www.digikey.com/short/abc1234")
        with patch("tools.hwrepo.digikey_handoff.send", return_value=reply) as send:
            self.request("GET")
            send.assert_not_called()
            status, _, body = self.handoff()
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["single_use_url"], reply.single_use_url)
            self.assertFalse(json.loads(body)["purchase_authorized"])
            self.assertEqual(self.handoff()[2], body)
            send.assert_called_once()
            payload = send.call_args.args[0]
            self.assertEqual(payload.root[0].requested_part_number, "RC0603FR-071KL")
            self.assertEqual(payload.root[0].quantities[0].quantity, 8)
            self.assertEqual(send.call_args.kwargs["list_name"], "controller")

    def test_new_preparation_rejects_other_tabs_old_review_before_send_or_cache(self) -> None:
        template = self.ready_order()
        assert template.plan is not None
        plan = template.plan
        def projected(root: Path, project_id: str, output: Path, runner: NetlistRunner, *,
                      boards: int, spare_percent: int, spare_minimum: int) -> PurchasingReport:
            updated = plan.model_copy(update={
                "preferences": PurchasingPreferences(boards=boards, spare_percent=spare_percent,
                                                     spare_minimum=spare_minimum),
                "lines": (plan.lines[0].model_copy(update={"required": boards * 2, "spares": 0,
                                                         "quantity": boards * 2}),),
            })
            return template.model_copy(update={"receipt_dir": str(output), "plan": updated})
        with patch("tools.hwrepo.parts_assistant.prepare", side_effect=projected):
            first = json.loads(self.request("POST", "order", "boards=1&spare_percent=0&spare_minimum=0")[2])
            second = json.loads(self.request("POST", "order", "boards=10&spare_percent=0&spare_minimum=0")[2])
        self.assertNotEqual(first["receipt_dir"], second["receipt_dir"])
        self.assertEqual(first["plan"]["lines"][0]["quantity"], 2)
        self.assertEqual(second["plan"]["lines"][0]["quantity"], 20)
        reply = DigiKeyHandoffReply(single_use_url="https://www.digikey.com/short/abc1234")
        with patch("tools.hwrepo.digikey_handoff.send", return_value=reply) as send:
            result = json.loads(self.handoff(first["receipt_dir"])[2])
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIsNone(result["single_use_url"])
            send.assert_not_called()
            result = json.loads(self.handoff(second["receipt_dir"])[2])
            self.assertEqual(result["status"], "READY")
            self.assertEqual(send.call_args.args[0].root[0].quantities[0].quantity, 20)
            stale = json.loads(self.handoff(first["receipt_dir"])[2])
            self.assertEqual(stale["status"], "BLOCKED")
            self.assertIsNone(stale["single_use_url"])
            self.assertEqual(json.loads(self.handoff(second["receipt_dir"])[2]), result)
            send.assert_called_once()

    def test_handoff_checks_board_and_catalog_freshness_before_sending(self) -> None:
        for relative in ("examples/projects/controller/project.json", "catalog/parts.json"):
            with self.subTest(relative=relative):
                self.ready_order()
                changed = self.root / relative
                changed.write_text(changed.read_text() + "\n", encoding="utf-8")
                with patch("tools.hwrepo.digikey_handoff.send") as send:
                    status, _, body = self.handoff()
                    self.assertEqual(status, 200)
                    self.assertEqual(json.loads(body)["status"], "BLOCKED")
                    self.assertIsNone(json.loads(body)["single_use_url"])
                    send.assert_not_called()
                self.assertIsNone(self.state.order)

    def test_handoff_changed_while_sending_does_not_return_stale_review_link(self) -> None:
        self.ready_order()
        def changed_reply(payload: DigiKeyHandoffPayload, *, list_name: str) -> DigiKeyHandoffReply:
            manifest = self.root / "examples/projects/controller/project.json"
            manifest.write_text(manifest.read_text() + "\n", encoding="utf-8")
            return DigiKeyHandoffReply(single_use_url="https://www.digikey.com/short/abc1234")
        with patch("tools.hwrepo.digikey_handoff.send", side_effect=changed_reply) as send:
            status, _, body = self.handoff()
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["status"], "BLOCKED")
            self.assertIsNone(json.loads(body)["single_use_url"])
            self.assertIn("may already have received", " ".join(json.loads(body)["issues"]))
            self.handoff()
            send.assert_called_once()
        self.assertEqual(self.request("GET", "download/digikey.csv")[0], 409)

    def test_handoff_network_failure_preserves_csv_and_never_implicitly_retries(self) -> None:
        report = self.ready_order()
        with patch("tools.hwrepo.digikey_handoff.send", side_effect=OSError("Connection lost")) as send:
            status, _, body = self.handoff()
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["status"], "ERROR")
            self.assertIsNone(json.loads(body)["single_use_url"])
            self.assertEqual(self.request("GET", "download/digikey.csv")[0], 200)
            self.assertEqual(self.handoff()[2], body)
            send.assert_called_once()
            with patch("tools.hwrepo.parts_assistant.prepare", return_value=report), patch(
                    "tools.hwrepo.parts_assistant.save_report"):
                self.assertEqual(self.request("POST", "order", "boards=3&spare_percent=0&spare_minimum=0")[0], 200)
            self.assertIsNone(self.state.handoff_result)
            self.handoff()
            self.assertEqual(send.call_count, 2)

    def test_cached_handoff_cannot_bypass_new_source_check(self) -> None:
        self.ready_order()
        reply = DigiKeyHandoffReply(single_use_url="https://www.digikey.com/short/abc1234")
        with patch("tools.hwrepo.digikey_handoff.send", return_value=reply) as send:
            self.handoff()
            catalog = self.root / "catalog/parts.json"
            catalog.write_text(catalog.read_text() + "\n", encoding="utf-8")
            result = json.loads(self.handoff()[2])
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIsNone(result["single_use_url"])
            send.assert_called_once()

    def test_order_form_passes_only_validated_quantities(self) -> None:
        report = PurchasingReport(project_id="controller", status="BLOCKED", receipt_dir="build/unused",
                                  issues=("Test capture unavailable",))
        with patch.object(Assistant, "prepare_order", return_value=report) as prepare:
            status, _, _ = self.request("POST", "order", urlencode({"boards": 5, "spare_percent": 10, "spare_minimum": 2}))
        self.assertEqual(status, 200)
        self.assertEqual(prepare.call_args.args[0], PurchasingPreferences(boards=5, spare_percent=10, spare_minimum=2))


if __name__ == "__main__":
    unittest.main()
