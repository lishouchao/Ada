"""
Ada D-Bus Service - D-Bus interface for Ada
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import D-Bus
try:
    import dbus
    import dbus.service
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logger.warning("D-Bus bindings not available")


class AdaDBusService:
    """
    D-Bus service for Ada.

    Provides a D-Bus interface for external applications
    to interact with Ada.

    Service: org.nebula.Ada
    Path: /org/nebula/Ada

    Interfaces:
    - org.nebula.Ada.Agent: Main agent interface
    - org.nebula.Ada.Skills: Skill management
    - org.nebula.Ada.Memory: Memory operations
    """

    BUS_NAME = "org.nebula.Ada"
    OBJECT_PATH = "/org/nebula/Ada"

    def __init__(self, agent=None):
        self.agent = agent
        self._bus = None
        self._loop = None
        self._running = False

    @property
    def is_available(self) -> bool:
        return DBUS_AVAILABLE

    async def start(self) -> bool:
        """Start the D-Bus service"""
        if not DBUS_AVAILABLE:
            logger.error("D-Bus bindings not available")
            return False

        try:
            # Get session bus
            self._bus = dbus.SessionBus()

            # Request bus name
            bus_name = dbus.service.BusName(self.BUS_NAME, self._bus)

            # Create GLib main loop
            from gi.repository import GLib
            self._loop = GLib.MainLoop()

            # Register objects
            self._register_objects(bus_name)

            self._running = True
            logger.info(f"D-Bus service started: {self.BUS_NAME}")

            # Run in background thread
            import threading
            thread = threading.Thread(target=self._run_loop, daemon=True)
            thread.start()

            return True

        except Exception as e:
            logger.error(f"Failed to start D-Bus service: {e}")
            return False

    def _register_objects(self, bus_name):
        """Register D-Bus objects"""

        # Create service objects
        if DBUS_AVAILABLE:
            self._agent_object = AgentDBusObject(
                bus_name,
                self.OBJECT_PATH,
                self.agent
            )
            self._skills_object = SkillsDBusObject(
                bus_name,
                f"{self.OBJECT_PATH}/Skills",
                self.agent
            )
            self._memory_object = MemoryDBusObject(
                bus_name,
                f"{self.OBJECT_PATH}/Memory",
                self.agent
            )

    def _run_loop(self):
        """Run GLib main loop"""
        if self._loop:
            try:
                self._loop.run()
            except Exception as e:
                logger.error(f"D-Bus loop error: {e}")

    async def stop(self):
        """Stop the D-Bus service"""
        self._running = False
        if self._loop:
            self._loop.quit()
        logger.info("D-Bus service stopped")


if DBUS_AVAILABLE:
    class AgentDBusObject(dbus.service.Object):
        """D-Bus object for main agent interface"""

        def __init__(self, bus_name, object_path, agent):
            super().__init__(bus_name, object_path)
            self.agent = agent

        @dbus.service.method("org.nebula.Ada.Agent",
                            in_signature="s", out_signature="s")
        def ProcessInput(self, text: str) -> str:
            """Process user input and return response"""
            import asyncio
            import json

            if not self.agent:
                return json.dumps({"error": "Agent not available"})

            try:
                # Run async in event loop
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(self.agent.process(text))
                loop.close()

                return json.dumps({
                    "success": result.success,
                    "message": result.message,
                    "output": result.output
                })
            except Exception as e:
                return json.dumps({"error": str(e)})

        @dbus.service.method("org.nebula.Ada.Agent",
                            in_signature="", out_signature="s")
        def GetStatus(self) -> str:
            """Get agent status"""
            import json

            if not self.agent:
                return json.dumps({"status": "unavailable"})

            return json.dumps({
                "status": "running",
                "mode": self.agent.mode.value if hasattr(self.agent, 'mode') else "normal",
                "skills_loaded": len(self.agent._registry) if hasattr(self.agent, '_registry') else 0
            })

        @dbus.service.method("org.nebula.Ada.Agent",
                            in_signature="s", out_signature="")
        def SetMode(self, mode: str) -> None:
            """Set agent mode"""
            if self.agent and hasattr(self.agent, 'set_mode'):
                self.agent.set_mode(mode)

        @dbus.service.signal("org.nebula.Ada.Agent")
        def ResponseReady(self, response: str):
            """Signal emitted when response is ready"""
            pass

    class SkillsDBusObject(dbus.service.Object):
        """D-Bus object for skill management"""

        def __init__(self, bus_name, object_path, agent):
            super().__init__(bus_name, object_path)
            self.agent = agent

        @dbus.service.method("org.nebula.Ada.Skills",
                            in_signature="", out_signature="s")
        def ListSkills(self) -> str:
            """List all available skills"""
            import json

            if not self.agent or not hasattr(self.agent, '_registry'):
                return json.dumps([])

            skills = []
            for skill in self.agent._registry.list_skills():
                skills.append({
                    "id": skill.metadata.id,
                    "name": skill.metadata.name,
                    "description": skill.metadata.description,
                    "category": skill.metadata.category
                })

            return json.dumps(skills)

        @dbus.service.method("org.nebula.Ada.Skills",
                            in_signature="s", out_signature="s")
        def GetSkillInfo(self, skill_id: str) -> str:
            """Get skill information"""
            import json

            if not self.agent or not hasattr(self.agent, '_registry'):
                return json.dumps({"error": "Agent not available"})

            metadata = self.agent._registry.get_skill_metadata(skill_id)
            if metadata:
                return json.dumps(metadata)
            return json.dumps({"error": "Skill not found"})

        @dbus.service.method("org.nebula.Ada.Skills",
                            in_signature="ss", out_signature="s")
        def ExecuteSkill(self, skill_id: str, input_text: str) -> str:
            """Execute a skill directly"""
            import asyncio
            import json

            if not self.agent:
                return json.dumps({"error": "Agent not available"})

            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    self.agent.execute_skill(skill_id, input_text)
                )
                loop.close()

                return json.dumps({
                    "success": result.success,
                    "message": result.message,
                    "output": result.output
                })
            except Exception as e:
                return json.dumps({"error": str(e)})

    class MemoryDBusObject(dbus.service.Object):
        """D-Bus object for memory operations"""

        def __init__(self, bus_name, object_path, agent):
            super().__init__(bus_name, object_path)
            self.agent = agent

        @dbus.service.method("org.nebula.Ada.Memory",
                            in_signature="ss", out_signature="s")
        def Store(self, content: str, memory_type: str) -> str:
            """Store a memory"""
            import asyncio
            import json

            if not self.agent or not hasattr(self.agent, '_memory'):
                return json.dumps({"error": "Memory not available"})

            try:
                from ada.memory.base import Memory, MemoryType

                memory = Memory(
                    content=content,
                    memory_type=MemoryType(memory_type)
                )

                loop = asyncio.new_event_loop()
                memory_id = loop.run_until_complete(
                    self.agent._memory.store(memory)
                )
                loop.close()

                return json.dumps({"id": memory_id})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @dbus.service.method("org.nebula.Ada.Memory",
                            in_signature="s", out_signature="s")
        def Retrieve(self, memory_id: str) -> str:
            """Retrieve a memory by ID"""
            import asyncio
            import json

            if not self.agent or not hasattr(self.agent, '_memory'):
                return json.dumps({"error": "Memory not available"})

            try:
                loop = asyncio.new_event_loop()
                memory = loop.run_until_complete(
                    self.agent._memory.retrieve(memory_id)
                )
                loop.close()

                if memory:
                    return json.dumps(memory.to_dict())
                return json.dumps({"error": "Memory not found"})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @dbus.service.method("org.nebula.Ada.Memory",
                            in_signature="si", out_signature="s")
        def Search(self, query: str, limit: int) -> str:
            """Search memories"""
            import asyncio
            import json

            if not self.agent or not hasattr(self.agent, '_memory'):
                return json.dumps([])

            try:
                from ada.memory.base import MemoryQuery

                query_obj = MemoryQuery(text=query, limit=limit)

                loop = asyncio.new_event_loop()
                memories = loop.run_until_complete(
                    self.agent._memory.search(query_obj)
                )
                loop.close()

                return json.dumps([m.to_dict() for m in memories])
            except Exception as e:
                return json.dumps({"error": str(e)})
else:
    # Placeholder classes when D-Bus is not available
    class AgentDBusObject:
        pass

    class SkillsDBusObject:
        pass

    class MemoryDBusObject:
        pass
