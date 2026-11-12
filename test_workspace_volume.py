from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from desktop_worker import Desktop


class VolumeTests(unittest.TestCase):
    def test_chat_paging_does_not_hide_old_rows_and_search_is_literal(self):
        with TemporaryDirectory() as directory:
            app=Desktop(Path(directory))
            try:
                with app.connect() as db:
                    db.executemany('INSERT INTO chats(id,title) VALUES(?,?)',[(f'{n:032x}',f'chat {n}') for n in range(120)])
                    db.execute('UPDATE chats SET title=? WHERE id=?',('100%_literal',f'{0:032x}'))
                ids=[]
                for offset in (0,50,100):
                    page=app.rpc('chats-page',{'offset':offset});self.assertEqual(page['total'],120)
                    self.assertLessEqual(len(page['items']),50);ids.extend(row[0] for row in page['items'])
                self.assertEqual(len(set(ids)),120)
                self.assertEqual(app.rpc('chats-page',{'query':'%_'})['total'],1)
                for offset in (-1,True,'1'):
                    with self.assertRaises(ValueError):app.rpc('chats-page',{'offset':offset})
            finally:app.close()
