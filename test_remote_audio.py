"""ACE-Step v1 uses the same transport, persistence and owner isolation as video."""
import test_remote_video


class RemoteAudioTests(test_remote_video.RemoteVideoTests):
    kind='audio'
    workflow='ace-step'
    suffix='.flac'
