from __future__ import annotations

import unittest
from datetime import date

from app.core.task_helpers import parse_quick_task


class QuickTaskParserTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 7, 8)

    def test_tomorrow_and_high_priority(self):
        task = parse_quick_task("pagar renta ma\u00f1ana alta", today=self.today)
        self.assertIsNotNone(task)
        self.assertEqual(task["tarea"], "pagar renta")
        self.assertEqual(task["deadline"], "2026-07-09")
        self.assertEqual(task["prioridad"], "alta")

    def test_daily_task(self):
        task = parse_quick_task("tomar medicina diaria", today=self.today)
        self.assertIsNotNone(task)
        self.assertEqual(task["tarea"], "tomar medicina")
        self.assertTrue(task["diaria"])

    def test_iso_date_and_low_priority(self):
        task = parse_quick_task("revisar reporte 2026-07-10 baja", today=self.today)
        self.assertIsNotNone(task)
        self.assertEqual(task["tarea"], "revisar reporte")
        self.assertEqual(task["deadline"], "2026-07-10")
        self.assertEqual(task["prioridad"], "baja")

    def test_plain_text_uses_default_deadline(self):
        task = parse_quick_task(
            "ordenar pendientes",
            default_deadline="2026-07-08",
            today=self.today,
        )
        self.assertIsNotNone(task)
        self.assertEqual(task["tarea"], "ordenar pendientes")
        self.assertEqual(task["deadline"], "2026-07-08")


if __name__ == "__main__":
    unittest.main()
