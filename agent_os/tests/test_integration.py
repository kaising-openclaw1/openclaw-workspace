"""
Agent OS — 集成测试
===================
验证所有核心子系统的协同工作
"""

import asyncio
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_os.core.event_bus import EventBus, Event, EventPriority, EventCategory
from agent_os.core.state_machine import StateMachine, State, TransitionError
from agent_os.core.plugin_system import PluginRegistry, PluginBase, PluginManifest
from agent_os.intelligence.router import (
    IntelligenceRouter, TaskProfile, TaskComplexity, IntelligenceLevel
)
from agent_os.security.crypto import KeyManager, CryptoEngine, EncryptedPayload
from agent_os.security.enclave import SecurityEnclave, AccessPolicy, AccessLevel, AuditAction
from agent_os.storage import ObjectStore, MessageQueue


class TestEventBus(unittest.TestCase):
    """事件总线测试"""

    def test_event_creation(self):
        event = Event(type="test.event", payload={"key": "value"})
        self.assertEqual(event.type, "test.event")
        self.assertEqual(event.payload["key"], "value")
        self.assertTrue(event.id)
        self.assertTrue(event.trace_id)

    def test_subscribe_and_publish(self):
        results = []

        async def handler(event):
            results.append(event.payload["msg"])

        async def run():
            bus = EventBus()
            bus.subscribe("test.*", handler)
            bus.start()
            await bus.emit("test.hello", {"msg": "world"})
            await asyncio.sleep(0.2)
            self.assertIn("world", results)
            await bus.stop()

        asyncio.run(run())

    def test_priority_ordering(self):
        events_order = []

        async def handler(event):
            events_order.append(event.priority.name)

        async def run():
            bus = EventBus()
            bus.subscribe("*", handler)
            bus.start()
            await bus.emit("low", {}, priority=EventPriority.LOW)
            await bus.emit("critical", {}, priority=EventPriority.CRITICAL)
            await bus.emit("normal", {}, priority=EventPriority.NORMAL)
            await asyncio.sleep(0.3)
            self.assertEqual(events_order[0], "CRITICAL")
            await bus.stop()

        asyncio.run(run())


class TestStateMachine(unittest.TestCase):
    """状态机测试"""

    def test_valid_transitions(self):
        async def run():
            sm = StateMachine(initial_state=State.PENDING)
            await sm.run()
            self.assertEqual(sm.state, State.RUNNING)
            await sm.complete()
            self.assertEqual(sm.state, State.COMPLETED)

        asyncio.run(run())

    def test_invalid_transition(self):
        async def run():
            sm = StateMachine(initial_state=State.COMPLETED)
            with self.assertRaises(TransitionError):
                await sm.transition(State.RUNNING)

        asyncio.run(run())

    def test_snapshot_restore(self):
        async def run():
            sm = StateMachine(initial_state=State.RUNNING)
            sm._context["test"] = "value"

            snap = sm.snapshot()
            self.assertEqual(snap.current_state, "RUNNING")
            self.assertEqual(snap.context["test"], "value")

            sm2 = StateMachine()
            await sm2.restore(snap)
            self.assertEqual(sm2.state, State.RUNNING)
            self.assertEqual(sm2.context["test"], "value")

        asyncio.run(run())

    def test_timeout(self):
        async def run():
            sm = StateMachine(initial_state=State.PENDING, timeout=0.1)
            await sm.run()
            self.assertEqual(sm.state, State.RUNNING)
            await asyncio.sleep(0.3)
            self.assertEqual(sm.state, State.TIMEOUT)

        asyncio.run(run())


class TestIntelligenceRouter(unittest.TestCase):
    """智力路由测试"""

    def setUp(self):
        self.router = IntelligenceRouter()

    def test_complexity_estimation(self):
        simple = TaskProfile(
            estimated_input_tokens=50,
            estimated_output_tokens=20,
            priority=1,
        )
        complex_task = TaskProfile(
            estimated_input_tokens=50000,
            estimated_output_tokens=10000,
            requires_tools=True,
            requires_vision=True,
            priority=10,
            security_level=5,
        )

        self.assertEqual(
            self.router.estimate_complexity(simple),
            TaskComplexity.TRIVIAL,
        )
        self.assertEqual(
            self.router.estimate_complexity(complex_task),
            TaskComplexity.VERY_COMPLEX,
        )

    def test_route_simple_task(self):
        task = TaskProfile(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            priority=1,
        )
        decision = self.router.route(task)
        self.assertIn(decision.intelligence_level,
                     [IntelligenceLevel.TINY, IntelligenceLevel.LIGHT])

    def test_route_complex_task(self):
        task = TaskProfile(
            estimated_input_tokens=50000,
            estimated_output_tokens=10000,
            requires_tools=True,
            priority=10,
        )
        decision = self.router.route(task)
        self.assertIn(decision.intelligence_level,
                     [IntelligenceLevel.HIGH, IntelligenceLevel.MAXIMUM])

    def test_model_registry(self):
        models = self.router.registry.list_models()
        self.assertGreater(len(models), 5)
        self.assertTrue(any(m["name"] == "deepseek-v4-flash" for m in models))


class TestSecurity(unittest.TestCase):
    """安全层测试"""

    def setUp(self):
        self.key_manager = KeyManager()
        self.crypto = CryptoEngine(self.key_manager)

    def test_encrypt_decrypt(self):
        plaintext = b"Hello Agent OS! This is sensitive source code."
        payload = self.crypto.encrypt(plaintext, context="test")
        decrypted = self.crypto.decrypt(payload, context="test")
        self.assertEqual(plaintext, decrypted)

    def test_context_isolation(self):
        plaintext = b"secret data"
        payload = self.crypto.encrypt(plaintext, context="ctx1")
        with self.assertRaises(Exception):
            self.crypto.decrypt(payload, context="ctx2")

    def test_key_derivation(self):
        key1 = self.key_manager.derive_key("context1")
        key2 = self.key_manager.derive_key("context2")
        self.assertNotEqual(key1, key2)

    def test_encrypted_payload_serialization(self):
        plaintext = b"test data"
        payload = self.crypto.encrypt(plaintext)
        data = payload.to_dict()
        restored = EncryptedPayload.from_dict(data)
        decrypted = self.crypto.decrypt(restored)
        self.assertEqual(plaintext, decrypted)


class TestSecurityEnclave(unittest.TestCase):
    """安全飞地测试"""

    def setUp(self):
        self.enclave = SecurityEnclave(data_dir="/tmp/agent-os-test-enclave")

    def tearDown(self):
        import shutil
        shutil.rmtree("/tmp/agent-os-test-enclave", ignore_errors=True)

    def test_access_policy(self):
        policy = AccessPolicy(
            subject="agent-1",
            resource_pattern="/projects/*",
            level=AccessLevel.READ,
        )
        self.enclave.add_policy(policy)
        self.assertTrue(
            self.enclave._check_access("agent-1", "/projects/myapp", AccessLevel.READ)
        )
        self.assertFalse(
            self.enclave._check_access("agent-1", "/projects/myapp", AccessLevel.WRITE)
        )
        self.assertFalse(
            self.enclave._check_access("agent-2", "/projects/myapp", AccessLevel.READ)
        )

    def test_audit_log(self):
        async def run():
            await self.enclave._audit(
                AuditAction.FILE_READ,
                actor="test-agent",
                resource="/test/file.py",
            )
            await self.enclave._flush_audit()
            entries = await self.enclave.query_audit(limit=10)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].actor, "test-agent")
            self.assertEqual(entries[0].action, AuditAction.FILE_READ)

        asyncio.run(run())


class TestStorage(unittest.TestCase):
    """存储层测试"""

    def setUp(self):
        self.store = ObjectStore(db_path="/tmp/agent-os-test.db")

    def tearDown(self):
        self.store.close()
        try:
            os.remove("/tmp/agent-os-test.db")
        except OSError:
            pass

    def test_put_get(self):
        self.store.put("test:key", {"hello": "world"})
        result = self.store.get("test:key")
        self.assertEqual(result["hello"], "world")

    def test_ttl_expiry(self):
        self.store.put("test:ttl", "expire_me", ttl=0.1)
        time.sleep(0.2)
        result = self.store.get("test:ttl")
        self.assertIsNone(result)

    def test_delete(self):
        self.store.put("test:del", "value")
        self.store.delete("test:del")
        result = self.store.get("test:del")
        self.assertIsNone(result)

    def test_list_prefix(self):
        self.store.put("user:1", "alice")
        self.store.put("user:2", "bob")
        self.store.put("config:app", "settings")
        keys = self.store.list_keys("user:")
        self.assertEqual(len(keys), 2)


class TestMessageQueue(unittest.TestCase):
    """消息队列测试"""

    def test_publish_subscribe(self):
        async def run():
            mq = MessageQueue()
            await mq.publish("test.topic", {"msg": "hello"})
            result = await mq.subscribe("test.topic", timeout=1.0)
            self.assertEqual(result["msg"], "hello")

        asyncio.run(run())

    def test_timeout(self):
        async def run():
            mq = MessageQueue()
            result = await mq.subscribe("empty.topic", timeout=0.1)
            self.assertIsNone(result)

        asyncio.run(run())


class TestPluginSystem(unittest.TestCase):
    """插件系统测试"""

    def test_plugin_lifecycle(self):
        class TestPlugin(PluginBase):
            async def initialize(self, config):
                self.register_tool(
                    "hello", "Say hello",
                    {"name": {"type": "string"}},
                    lambda name: f"Hello {name}!",
                )
                return True

        async def run():
            registry = PluginRegistry()
            plugin = TestPlugin()
            registry._plugins["test"] = plugin
            success = await registry.load("test")
            self.assertTrue(success)
            self.assertIsNotNone(registry.get_tool("hello"))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
