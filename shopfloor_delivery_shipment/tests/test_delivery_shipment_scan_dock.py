# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from .test_delivery_shipment_base import DeliveryShipmentCommonCase


class DeliveryShipmentScanDockCase(DeliveryShipmentCommonCase):
    """Tests for '/scan_dock' endpoint."""

    def test_scan_dock_barcode_not_found(self):
        response = self.service.dispatch("scan_dock", params={"barcode": "UNKNOWN"})
        self.assert_response_scan_dock(
            response, message=self.service.msg_store.barcode_not_found()
        )

    def test_scan_dock_no_shipment_in_progress(self):
        response = self.service.dispatch(
            "scan_dock", params={"barcode": self.dock.barcode}
        )
        self.assert_response_scan_dock(
            response, message=self.service.msg_store.no_shipment_in_progress()
        )

    def test_scan_dock_create_shipment_if_none(self):
        self.menu.sudo().allow_shipment_advice_create = True
        # First scan, a confirmation is required to create a new shipment
        response = self.service.dispatch(
            "scan_dock", params={"barcode": self.dock.barcode}
        )
        self.assert_response_scan_dock(
            response,
            message=self.service.msg_store.scan_dock_again_to_confirm(self.dock),
            confirmation_required=self.dock.barcode,
        )
        # Second scan to confirm
        response = self.service.dispatch(
            "scan_dock",
            params={"barcode": self.dock.barcode, "confirmation": self.dock.barcode},
        )
        new_shipment = self.env["shipment.advice"].search(
            [("state", "=", "in_progress"), ("dock_id", "=", self.dock.id)],
            limit=1,
            order="create_date DESC",
        )
        self.assert_response_scan_document(response, new_shipment)

    def test_scan_dock_create_shipment_confirmation_not_same_dock(self):
        self.menu.sudo().allow_shipment_advice_create = True
        # First scan, a confirmation is required to create a new shipment
        response = self.service.dispatch(
            "scan_dock", params={"barcode": self.dock.barcode}
        )
        self.assert_response_scan_dock(
            response,
            message=self.service.msg_store.scan_dock_again_to_confirm(self.dock),
            confirmation_required=self.dock.barcode,
        )
        # Then scan a different dock barcode whith the confirmation of the previous dock
        response = self.service.dispatch(
            "scan_dock",
            params={"barcode": self.dock2.barcode, "confirmation": self.dock.barcode},
        )
        # Return a confirmation for the last dock scanned
        self.assert_response_scan_dock(
            response,
            message=self.service.msg_store.scan_dock_again_to_confirm(self.dock2),
            confirmation_required=self.dock2.barcode,
        )

    def test_scan_dock_with_planned_content_ok(self):
        self._plan_records_in_shipment(self.shipment, self.pickings)
        self.shipment.action_confirm()
        self.shipment.action_in_progress()
        response = self.service.dispatch(
            "scan_dock", params={"barcode": self.dock.barcode}
        )
        self.assert_response_scan_document(response, self.shipment)

    def test_scan_dock_without_planned_content_ok(self):
        self.shipment.action_confirm()
        self.shipment.action_in_progress()
        response = self.service.dispatch(
            "scan_dock", params={"barcode": self.dock.barcode}
        )
        self.assert_response_scan_document(response, self.shipment)

    def test_scan_dock_with_partially_loaded_transfers(self):
        package_level = self.picking1.package_level_ids
        scanned_package = package_level.package_id
        # Load partially a transfer
        self.shipment.action_confirm()
        self.shipment.action_in_progress()
        response = self.service.dispatch(
            "scan_document",
            params={
                "shipment_advice_id": self.shipment.id,
                "barcode": scanned_package.name,
            },
        )
        # Scan the dock to check the content to load among partially loaded transfers
        response = self.service.dispatch(
            "scan_dock", params={"barcode": self.dock.barcode}
        )
        lines_to_load = self.picking1.move_line_ids.filtered(
            lambda l: l.package_id != scanned_package
        )
        self.assert_response_scan_document(
            response, self.shipment, lines_to_load=lines_to_load
        )
