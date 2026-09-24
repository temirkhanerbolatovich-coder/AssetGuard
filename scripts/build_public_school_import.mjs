import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = new URL("../outputs/public-school-import/", import.meta.url);
const outputPath = new URL("school-inventory-rk-demo.xlsx", outputDir);
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Импорт в AssetGuard");
sheet.showGridLines = false;
sheet.getRange("A1:I5").values = [
  ["Инвентарный номер", "Наименование", "Тип оборудования", "Организация", "Корпус", "Этаж", "Кабинет", "Статус", "Примечание"],
  ["DEMO-KZ-OS10-211-001", "Интерактивная доска", "Прочее", "Публичный demo РК — ОШ №10 Караганда", "не указан", "не указан", "211", "ACTIVE", "Упомянута в паспорте школы для кабинета физики"],
  ["DEMO-KZ-OS10-211-002", "Монитор", "Прочее", "Публичный demo РК — ОШ №10 Караганда", "не указан", "не указан", "211", "ACTIVE", "Упомянут в паспорте школы для кабинета физики"],
  ["DEMO-KZ-OS10-211-003", "Системный блок", "ПК", "Публичный demo РК — ОШ №10 Караганда", "не указан", "не указан", "211", "ACTIVE", "Упомянут в паспорте школы для кабинета физики"],
  ["DEMO-KZ-OS10-211-004", "Блок питания", "Прочее", "Публичный demo РК — ОШ №10 Караганда", "не указан", "не указан", "211", "ACTIVE", "Упомянут в паспорте школы для кабинета физики"],
];
sheet.getRange("A1:I1").format = { fill: "#17365D", font: { name: "Arial", bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("A1:I5").format.font = { name: "Arial", size: 10 };
sheet.getRange("A1:I5").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
sheet.getRange("A2:I5").format.wrapText = true;
sheet.getRange("A:A").format.columnWidth = 26;
sheet.getRange("B:B").format.columnWidth = 24;
sheet.getRange("C:C").format.columnWidth = 18;
sheet.getRange("D:D").format.columnWidth = 34;
sheet.getRange("E:H").format.columnWidth = 15;
sheet.getRange("I:I").format.columnWidth = 44;
sheet.freezePanes.freezeRows(1);

const source = workbook.worksheets.add("Источник");
source.getRange("A1").values = [["Публичный demo-набор для проверки импорта"]];
source.getRange("A2").values = [["Источник фактов: паспорт КГУ «ОШ №10», г. Караганда."]];
source.getRange("A3").values = [["https://kargoo.kz/content/view/78/321317415?lang=ru"]];
source.getRange("A4").values = [["Инвентарные номера DEMO-KZ-* созданы AssetGuard только для теста и не являются номерами школы."]];
source.getRange("A1:A4").format = { font: { name: "Arial", size: 11 }, wrapText: true };
source.getRange("A1").format.font = { name: "Arial", size: 13, bold: true, color: "#17365D" };
source.getRange("A:A").format.columnWidth = 100;

const check = await workbook.inspect({ kind: "table", range: "Импорт в AssetGuard!A1:I5", include: "values", tableMaxRows: 5, tableMaxCols: 9 });
console.log(check.ndjson);
const preview = await workbook.render({ sheetName: "Импорт в AssetGuard", range: "A1:I5", scale: 1.2, format: "png" });
await fs.writeFile(new URL("school-inventory-rk-demo.png", outputDir), new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(fileURLToPath(outputPath));
