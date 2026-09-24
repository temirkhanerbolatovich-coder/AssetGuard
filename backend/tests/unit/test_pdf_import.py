from assetguard.interfaces.http.admin_assets import _government_inventory_rows


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
