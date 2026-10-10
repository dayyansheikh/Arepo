"""Read-only original-build recovery in isolated local Git/process fixtures."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store.capture import _digest, _json_bytes
from astrolabe.research_panel.frame import GammaFrameRun
from astrolabe.research_panel.original_reader import read_original_frame
from tests.unit.test_feature_store_capture import Stream


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE,
                                   env={'PATH': os.defpath}).decode().strip()


@pytest.fixture
def original_code(tmp_path):
    # This disposable Git fixture is not a replacement of the user's repository.
    repo = tmp_path / 'original_code'
    package = repo / 'backend' / 'astrolabe'
    package.mkdir(parents=True)
    source = Path(__file__).parents[2] / 'astrolabe'
    shutil.copyfile(source / '__init__.py', package / '__init__.py')
    for name in ('feature_store', 'research_panel'):
        (package / name).mkdir()
        for file in (source / name).glob('*.py'):
            shutil.copyfile(file, package / name / file.name)
    git(repo, 'init', '--quiet')
    git(repo, 'add', 'backend')
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Original code fixture')
    return repo, git(repo, 'rev-parse', 'HEAD')


async def captured(tmp_path):
    root = tmp_path.resolve() / 'fs2_capture_original'
    run = GammaFrameRun(root, transport=httpx.MockTransport(
        lambda r: httpx.Response(200, stream=Stream([b'{"markets":[]}']))))
    report = await run.collect()
    return root, report


def read(root, code, tmp_path, suffix='success'):
    repo, commit = code
    return read_original_frame(root, implementation_commit=commit, repository=repo,
                               output_root=tmp_path.resolve() / ('fs2_frame_read_' + suffix))


async def test_original_reader_verifies_exact_code_and_preserves_source_and_worktree(
    tmp_path, original_code,
):
    root, report = await captured(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    repo, commit = original_code
    result = read(root, original_code, tmp_path)
    assert result['report'] == report
    receipt = result['read_receipt']
    assert receipt['original_provenance_class'] == 'synthetic'
    assert not receipt['origin_admitted'] and not receipt['observation_clocks_changed']
    assert report['frame_available_at']['utc'] <= receipt['metadata_read_started_at']['utc']
    assert receipt['metadata_read_started_at']['utc'] <= receipt['verification_started_at']['utc']
    assert receipt['verification_started_at']['utc'] <= receipt['completed_at']['utc']
    assert receipt['completed_at']['utc'] <= result['read_available_at']['utc']
    assert git(repo, 'rev-parse', 'HEAD') == commit
    assert not git(repo, 'status', '--porcelain')
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):
        read(root, original_code, tmp_path)
    assert read(root, original_code, tmp_path, 'fresh')['report'] == report


async def test_wrong_commit_or_changed_package_cannot_substitute_parser(tmp_path, original_code):
    root, _ = await captured(tmp_path)
    repo, _ = original_code
    file = repo / 'backend/astrolabe/research_panel/frame.py'
    file.write_text(file.read_text() + '\n# changed build fixture\n')
    git(repo, 'add', 'backend')
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Changed build fixture')
    with pytest.raises(ValueError, match='hash differs'):
        read(root, (repo, git(repo, 'rev-parse', 'HEAD')), tmp_path)
    assert not (tmp_path / 'fs2_frame_read_success').exists()


async def test_original_verification_refuses_corruption_and_retains_failed_read(
    tmp_path, original_code,
):
    root, _ = await captured(tmp_path)
    folder = next(p for p in root.iterdir() if p.is_dir())
    (folder / 'raw.bin').write_bytes(b'corrupt synthetic fixture')
    with pytest.raises(ValueError, match='original-build verification refused'):
        read(root, original_code, tmp_path)
    output = tmp_path / 'fs2_frame_read_success'
    assert (output / 'read_failure_ack.json').exists()
    assert not (output / 'read_receipt_ack.json').exists()
    assert (folder / 'raw.bin').read_bytes() == b'corrupt synthetic fixture'


async def test_current_environment_cannot_claim_original_library_build(tmp_path, original_code):
    root, _ = await captured(tmp_path)
    # Synthetic fully rehashed metadata: the child must still check actual dependencies.
    policy_file = root / 'frame_policy.json'
    policy = json.loads(policy_file.read_bytes())
    policy['build']['source_build']['libraries']['httpx'] = '0.0.synthetic'
    policy_file.write_bytes(_json_bytes(policy))
    ack_file = root / 'frame_policy_ack.json'
    ack = json.loads(ack_file.read_bytes())
    ack['payload_hash'] = _digest(policy_file.read_bytes())
    ack_file.write_bytes(_json_bytes(ack))
    report_file = root / 'frame_report.json'
    report = json.loads(report_file.read_bytes())
    report['policy_hash'] = ack['payload_hash']
    report_file.write_bytes(_json_bytes(report))
    report_ack_file = root / 'frame_report_ack.json'
    report_ack = json.loads(report_ack_file.read_bytes())
    report_ack['payload_hash'] = _digest(report_file.read_bytes())
    report_ack_file.write_bytes(_json_bytes(report_ack))
    with pytest.raises(ValueError, match='original-build verification refused'):
        read(root, original_code, tmp_path)


@pytest.mark.parametrize('commit', ['HEAD', '--all', '../path', 'a' * 39, 'A' * 40])
async def test_original_read_requires_full_commit_not_mutable_refs(tmp_path, original_code, commit):
    root, _ = await captured(tmp_path)
    with pytest.raises(ValueError, match='immutable Git commit'):
        read(root, (original_code[0], commit), tmp_path)
    assert not (tmp_path / 'fs2_frame_read_success').exists()


async def test_original_read_refuses_output_inside_evidence(tmp_path, original_code):
    root, _ = await captured(tmp_path)
    with pytest.raises(ValueError, match='separate fresh'):
        read_original_frame(
            root, implementation_commit=original_code[1], repository=original_code[0],
            output_root=root / 'fs2_frame_read_wrong',
        )
