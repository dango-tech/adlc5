"""Reject incomplete, altered or mismatched registry publication inputs."""
import hashlib
import importlib.util
import json
import io
import tarfile
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/verify-plugin-release.py')
release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for host in ('codex', 'claude-code', 'cursor', 'hermes'):
            self.archive(host)
            self.archive(host, suffix='tar.gz')
        self.checksums()

    def archive(self, label, suffix='zip', **changes):
        metadata = dict(host='claude' if label == 'claude-code' else label, version='5.1.0', source_revision='a'*40, source_dirty=False)
        metadata.update(changes)
        data = json.dumps(metadata).encode()
        path = self.directory / f'adlc5-{label}-plugin-5.1.0.{suffix}'
        if suffix == 'zip':
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('INSTALL.json', data)
        else:
            prefix = 'adlc5-5.1.0' if label == 'claude-code' else f'adlc5-{label}-5.1.0'
            with tarfile.open(path, 'w:gz') as archive:
                member = tarfile.TarInfo(prefix + '/INSTALL.json')
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))

    def checksums(self):
        (self.directory / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(self.directory.glob('adlc5-*'))))

    def test_valid_release(self):
        self.assertEqual(release.verify(self.directory, '5.1.0'), 'a'*40)

    def test_missing_or_duplicate_archive(self):
        path = self.directory / 'SHA256SUMS'
        original = path.read_text()
        for contents in (original.splitlines(keepends=True)[0], original+original):
            path.write_text(contents)
            with self.assertRaises(ValueError): release.verify(self.directory, '5.1.0')

    def test_modified_archive(self):
        next(self.directory.glob('*.tar.gz')).write_bytes(b'altered')
        with self.assertRaises(ValueError): release.verify(self.directory, '5.1.0')

    def test_invalid_provenance(self):
        for changes in ({'version':'5.0.0'}, {'host':'hermes'}, {'source_dirty':True}, {'source_revision':'b'*40}):
            self.archive('codex', **changes); self.checksums()
            with self.assertRaises(ValueError): release.verify(self.directory, '5.1.0')

    def test_invalid_tar_provenance(self):
        for changes in ({'version':'5.0.0'}, {'host':'hermes'}, {'source_dirty':True}, {'source_revision':'b'*40}):
            self.archive('codex', suffix='tar.gz', **changes); self.checksums()
            with self.assertRaises(ValueError): release.verify(self.directory, '5.1.0')

    def test_non_archive_tar_with_valid_checksum(self):
        next(self.directory.glob('*.tar.gz')).write_bytes(b'not an archive')
        self.checksums()
        with self.assertRaises(tarfile.ReadError): release.verify(self.directory, '5.1.0')

    def test_unexpected_path(self):
        path = self.directory / 'SHA256SUMS'
        path.write_text(path.read_text().replace('adlc5-codex-plugin-5.1.0.zip','../adlc5-codex-plugin-5.1.0.zip'))
        with self.assertRaises(ValueError): release.verify(self.directory, '5.1.0')


if __name__ == '__main__': unittest.main()
