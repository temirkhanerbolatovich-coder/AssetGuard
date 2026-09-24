from io import BytesIO
from types import ModuleType, SimpleNamespace
from starlette.datastructures import UploadFile
from sqlalchemy import select

from assetguard.infrastructure.database import get_session_factory
from assetguard.interfaces.http import admin_assets
from assetguard.interfaces.http.admin_assets import _asset_category_from_import, _asset_type_from_import, _government_inventory_rows
from assetguard.modules.assets.models import AssetRecord
from assetguard.modules.identity.auth import AuthPrincipal


def test_maps_kazakhstan_accounting_inventory_statement_to_grouped_assets() -> None:
    table = [
        ["№ строки", "Наименование долгосрочных активов", "Номенклатурный номер", "Единица", "Цена", "Количество", "Сумма", "Количество", "Сумма, тенге", "Примечание", "№ строки"],
        ["24", "кабинет физики 1комп", "236006000003", "шт", "2 915 000,00", "", "", "1,000", "2 915 000,00", "", "24"],
        ["25", "компьютер в комплекте", "236006000025", "шт", "94 490,00", "", "", "1,000", "94 490,00", "", "25"],
    ]

    rows = _government_inventory_rows(table, "3333.pdf")

    assert len(rows) == 2
    assert rows[0]["inventory_number"] == "PDF-3333-24"
    assert rows[1]["asset_type"] == "Desktop"
    assert "Номенклатурный номер: 236006000025." in (rows[1]["notes"] or "")


def test_government_rows_keep_repeated_sequence_numbers_unique_between_pages() -> None:
    table = [["№ строки", "Наименование", "Номенклатурный номер", "Единица", "Цена", "Количество", "Сумма", "Количество", "Сумма", "Примечание", "№ строки"],
             ["1", "Парта ученическая", "123456", "шт", "1", "", "", "1", "1", "", "1"]]

    first_page = _government_inventory_rows(table, "school.pdf", page_number=1)
    second_page = _government_inventory_rows(table, "school.pdf", page_number=2)

    assert first_page[0]["inventory_number"] == "PDF-school-P1-1"
    assert second_page[0]["inventory_number"] == "PDF-school-P2-1"


def test_pdf_import_combines_government_statement_rows_across_all_pages(monkeypatch) -> None:
    table = [["№ строки", "Наименование долгосрочных активов", "Номенклатурный номер", "Единица", "Цена", "Количество", "Сумма", "Количество", "Сумма, тенге", "Примечание", "№ строки"],
             ["1", "Парта ученическая", "123456", "шт", "1", "", "", "1", "1", "", "1"]]

    class Page:
        def extract_tables(self):
            return [table]

    class Document:
        pages = [Page(), Page()]
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return None

    monkeypatch.setattr(admin_assets.pdfplumber, "open", lambda *_: Document())
    with get_session_factory()() as session:
        result = admin_assets.import_assets_pdf(
            UploadFile(filename="school.pdf", file=BytesIO(b"test")), session,
            AuthPrincipal(user_id=None, username="bootstrap-admin", role="ADMIN", session_id=None, organization_id=None),
            apply=False,
        )

    assert result["rows"] == 2
    assert [item["inventory_number"] for item in result["samples"]] == [
        "PDF-school-P1-1", "PDF-school-P2-1",
    ]
    assert [item["row"] for item in result["items"]] == [1, 2]
    assert [item["action"] for item in result["items"]] == ["create", "create"]


def test_scanned_pdf_ocr_accepts_only_bracketed_item_rows(monkeypatch) -> None:
    words = ["1", "Парта", "ученическая", "1234567", "шт", "1"]
    data = {
        "text": words, "conf": ["96"] * len(words), "page_num": [1] * len(words),
        "block_num": [1] * len(words), "par_num": [1] * len(words), "line_num": [1] * len(words),
        "left": [index * 20 for index in range(len(words))],
    }

    class Rendered:
        def to_pil(self):
            return object()
    class Page:
        def render(self, **_):
            return Rendered()
    class PdfDocument:
        def __init__(self, _):
            self.pages = [Page()]
        def __len__(self):
            return len(self.pages)
        def __getitem__(self, index):
            return self.pages[index]

    pdfium = ModuleType("pypdfium2")
    pdfium.PdfDocument = PdfDocument
    pytesseract = ModuleType("pytesseract")
    pytesseract.Output = SimpleNamespace(DICT="dict")
    calls = []
    pytesseract.image_to_data = lambda *_, **kwargs: calls.append(kwargs) or data
    monkeypatch.setitem(__import__("sys").modules, "pypdfium2", pdfium)
    monkeypatch.setitem(__import__("sys").modules, "pytesseract", pytesseract)
    monkeypatch.setattr(admin_assets, "get_settings", lambda: SimpleNamespace(tesseract_cmd=None, tesseract_data_dir=r"C:\AssetGuardOCR\tessdata"))

    parsed = admin_assets._ocr_government_inventory_pdf(b"pdf", "scan.pdf")

    assert len(parsed) == 1
    assert parsed[0]["name"] == "Парта ученическая"
    assert parsed[0]["inventory_number"] == "PDF-scan-P1-1"
    assert "OCR" in (parsed[0]["notes"] or "")
    assert parsed[0]["_ocr_confidence"] == 96
    assert "--tessdata-dir C:\\AssetGuardOCR\\tessdata" in calls[0]["config"]

    pytesseract.image_to_data = lambda *_, **__: {**data, "text": ["Пустой", "бланк"], "conf": ["96", "96"], "page_num": [1, 1], "block_num": [1, 1], "par_num": [1, 1], "line_num": [1, 1], "left": [0, 20]}
    assert admin_assets._ocr_government_inventory_pdf(b"pdf", "blank.pdf") == []


def test_import_preview_returns_all_rows_and_can_skip_selected_rows(monkeypatch) -> None:
    principal = AuthPrincipal(user_id=None, username="bootstrap-admin", role="ADMIN", session_id=None, organization_id=None)
    rows = [
        {
            "inventory_number": f"SKIP-{index}", "name": f"Asset {index}", "asset_type": "Other",
            "status": "ACTIVE", "category": "OTHER", "organization": None,
            "building": None, "floor": None, "room": None, "notes": None,
        }
        for index in range(30)
    ]
    with get_session_factory()() as session:
        preview = admin_assets._import_assets(rows, session, principal, apply=False, source="xlsx")
        assert preview["rows"] == 30
        assert len(preview["items"]) == 30
        assert preview["items"][24]["row"] == 25

        monkeypatch.setattr(session, "commit", lambda: None)
        applied = admin_assets._import_assets(
            rows[:2], session, principal, apply=True, source="xlsx", excluded_rows={0},
        )
        assert applied == {"rows": 1, "creates": 1, "updates": 0, "applied": True}
        imported_numbers = set(session.scalars(select(AssetRecord.inventory_number).where(AssetRecord.inventory_number.in_({"SKIP-0", "SKIP-1"}))))
        assert imported_numbers == {"SKIP-1"}
        session.rollback()


def test_import_classifies_school_property_instead_of_defaulting_everything_to_it() -> None:
    assert _asset_type_from_import("Парта ученическая") == "Furniture"
    assert _asset_category_from_import(None, "Furniture") == "FURNITURE"
    assert _asset_type_from_import("Мячи футбольные") == "Sports"
    assert _asset_category_from_import(None, "Sports") == "SPORTS"
    assert _asset_type_from_import("Микроскоп учебный") == "Educational"
    assert _asset_category_from_import("Мебель", "Other") == "FURNITURE"
