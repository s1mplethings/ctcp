import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from csv_cleaner_web.service import CleaningOptions, clean_csv_text


CSV_TEXT = '\n'.join([
    'id,name,city,amount',
    '1,Ada,Shanghai,120',
    '2,Ben,,85',
    ',,,',
    '2,Ben,,85',
    '3,Caro,Shenzhen,210',
]) + '\n'


class CsvCleanerServiceTests(unittest.TestCase):
    def test_clean_csv_text_removes_empty_and_duplicates(self) -> None:
        result = clean_csv_text(CSV_TEXT, CleaningOptions(remove_empty_rows=True, remove_duplicates=True))
        self.assertEqual(result.stats['input_rows'], 5)
        self.assertEqual(result.stats['removed_empty_rows'], 1)
        self.assertEqual(result.stats['removed_duplicate_rows'], 1)
        self.assertEqual(result.stats['output_rows'], 3)

    def test_clean_csv_text_keeps_selected_columns(self) -> None:
        result = clean_csv_text(CSV_TEXT, CleaningOptions(keep_columns=['name', 'amount']))
        self.assertEqual(result.columns, ['name', 'amount'])
        self.assertIn('name,amount', result.cleaned_csv)


if __name__ == '__main__':
    unittest.main()
