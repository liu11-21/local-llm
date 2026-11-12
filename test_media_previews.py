from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import base64
from media_previews import MediaPreviews


class MediaPreviewTests(TestCase):
    def test_bounded_derived_cache_invalidates_changed_original_and_preserves_originals(self):
        image=(Path(__file__).parent/'desktop/tests/media-fixtures/sample.png').read_bytes()
        data='data:image/png;base64,'+base64.b64encode(image).decode()
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();source=root/'a12345678901.png';source.write_bytes(image)
            cache=MediaPreviews(root)
            self.assertEqual(cache.get([source.name]),{})
            cache.put(source.name,data)
            self.assertEqual(cache.get([source.name])[source.name],data)
            source.write_bytes(image+b'changed identity')
            self.assertEqual(cache.get([source.name]),{})
            second=root/'b12345678901.png';second.write_bytes(image)
            with patch('media_previews.LIMIT',0):cache.put(second.name,data)
            self.assertFalse(list(cache.root.glob('*.png')))
            self.assertTrue(second.exists());self.assertTrue(source.exists())
            for name,payload in [('../secret.png',data),(second.name,'data:image/svg+xml;base64,bad')]:
                with self.assertRaises(ValueError):cache.put(name,payload)

    def test_library_runtime_filter_pagination_does_not_read_original_media(self):
        import json
        from desktop_worker import Desktop
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder));app.outputs.mkdir(exist_ok=True)
            try:
                with app.connect() as db:
                    for index in range(60):
                        name=f'{index:012x}.png';(app.outputs/name).write_bytes(b'not decoded while listing')
                        db.execute('INSERT INTO creations VALUES(?,?)',(name,json.dumps({'model':'fixture','runtime':'local-comfyui' if index%2 else 'remote-comfyui','source':{'host':'a'*32} if not index%2 else {}})))
                with patch('pathlib.Path.read_bytes',side_effect=AssertionError('must not load originals')):
                    page=app.works({'runtime':'a'*32,'offset':24})
                self.assertEqual(page['total'],30);self.assertEqual(len(page['items']),6)
            finally:app.close()
