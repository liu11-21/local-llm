import unittest

from onboarding import onboarding_plan
from runtime_contract import capability


class OnboardingTests(unittest.TestCase):
    def test_remote_video_and_audio_first_use_preserves_privacy_and_media_task_mapping(self):
        for task,kind,workflow in [('video','video','wan21'),('music','audio','ace-step')]:
            remote=capability('p','Media desk','remote-host','Local LLM',connected=True,health='unhealthy',tasks=['chat',task],
                task_health={'chat':'unhealthy',task:'ready'},media={kind:{'state':'ready','installed':True,'workflows':[workflow],'schema':2}})
            selected=onboarding_plan(self.info(),[remote],task,'auto')['choices'][0]
            self.assertEqual((selected['runtime'],selected['model'],selected['actions']),('p',workflow,[]))
            self.assertEqual(len(onboarding_plan(self.info(),[remote],task,'privacy')['choices']),1)

    def info(self, installed=(), engine=False):
        return {"hardware":{"ram_available":None}, "registry":{"models":list(installed)}, "engine":engine,
                "recommended":[{"name":"small.gguf","repo":"owner/Small","description":"輕量中文對話",
                                "fit":"待確認","size":4,"url":"https://example.test/fixed"},
                               {"name":"large.gguf","repo":"owner/Large","description":"中文",
                                "fit":"記憶體不足","size":8,"url":"https://example.test/large"}]}

    def test_cpu_or_unknown_hardware_can_prepare_a_small_model(self):
        choices = onboarding_plan(self.info(), [], "chat", "auto")["choices"]
        self.assertEqual([item["model"] for item in choices], ["small.gguf"])
        self.assertEqual([step["action"] for step in choices[0]["actions"]], ["engine-install","download"])
        self.assertEqual(onboarding_plan(self.info(engine=True), [], "chat", "auto")["choices"][0]["actions"][0]["action"], "download")

    def test_existing_models_and_privacy(self):
        model = {"id":"installed.gguf","label":"Existing","ram":2,"bytes":1}
        remote = capability("p","Desk","remote-host","Local LLM",connected=True,health="ready",tasks=["chat"],models=["remote"])
        self.assertEqual(onboarding_plan(self.info([model],True), [remote], "chat", "privacy")["choices"][0]["actions"], [])
        self.assertEqual(len(onboarding_plan(self.info([model],True), [remote], "chat", "privacy")["choices"]), 1)
        self.assertEqual(len(onboarding_plan(self.info([model],True), [remote], "chat", "auto")["choices"]), 2)
        self.assertTrue(onboarding_plan(self.info(), [], "image", "auto")["media"])

    def test_ready_image_host_does_not_require_local_install_or_healthy_text(self):
        remote = capability("p","Image desk","remote-host","Local LLM", connected=True,health="unhealthy",
                            tasks=["chat","image"],task_health={"chat":"unhealthy","image":"ready"},
                            media={"image":{"state":"ready","installed":True,"workflows":["sd15"]}})
        choice = onboarding_plan(self.info(),[remote],"image","auto")["choices"][0]
        self.assertEqual((choice["runtime"],choice["model"],choice["actions"]),("p","sd15",[]))
        self.assertEqual(len(onboarding_plan(self.info(),[remote],"image","privacy")["choices"]),1)
        remote["checked_at"] = 0
        self.assertEqual(len(onboarding_plan(self.info(),[remote],"image","auto")["choices"]),1)
