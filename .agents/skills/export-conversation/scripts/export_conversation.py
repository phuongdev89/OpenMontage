#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_conversation.py - Antigravity Conversation & Transcript Exporter

Exports the full conversation history, terminal command executions, background tasks,
and recursively extracts subagent sessions into structured Markdown (.md) and JSON (.json).

Zero external dependencies - uses standard Python library only.
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_default_brain_dir() -> Path:
    """Detect the local Antigravity transcript root, with an explicit override."""
    env_dir = os.environ.get("EXPORT_CONVERSATION_BRAIN_DIR") or os.environ.get("ANTIGRAVITY_BRAIN_DIR") or os.environ.get("GEMINI_BRAIN_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.home() / ".gemini" / "antigravity" / "brain"


def find_latest_conversation(brain_dir: Path) -> Optional[str]:
    """Find the most recently modified conversation ID in the brain directory."""
    if not brain_dir.exists():
        return None

    candidates: List[Tuple[float, str]] = []
    for item in brain_dir.iterdir():
        if not item.is_dir():
            continue
        # Check if it has .system_generated/logs/transcript*.jsonl
        logs_dir = item / ".system_generated" / "logs"
        if logs_dir.exists():
            tf = logs_dir / "transcript_full.jsonl"
            t = logs_dir / "transcript.jsonl"
            target_file = tf if tf.exists() else (t if t.exists() else None)
            if target_file:
                candidates.append((target_file.stat().st_mtime, item.name))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def clean_user_content(raw_content: str) -> Tuple[str, Dict[str, str]]:
    """
    Extract clean prompt from raw user message that may contain system tags like
    <USER_REQUEST>, <ADDITIONAL_METADATA>, <USER_SETTINGS_CHANGE>, etc.
    """
    metadata: Dict[str, str] = {}
    
    # Check for <USER_REQUEST>...</USER_REQUEST>
    req_match = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_content, re.DOTALL)
    clean_text = req_match.group(1).strip() if req_match else raw_content.strip()

    # Extract metadata blocks if present
    meta_match = re.search(r"<ADDITIONAL_METADATA>(.*?)</ADDITIONAL_METADATA>", raw_content, re.DOTALL)
    if meta_match:
        metadata["additional_metadata"] = meta_match.group(1).strip()

    settings_match = re.search(r"<USER_SETTINGS_CHANGE>(.*?)</USER_SETTINGS_CHANGE>", raw_content, re.DOTALL)
    if settings_match:
        metadata["settings_change"] = settings_match.group(1).strip()

    return clean_text, metadata


def parse_exit_code(content: str) -> Optional[int]:
    """Extract exit code from command execution output string."""
    m = re.search(r"exited with code (\d+)", content)
    if m:
        return int(m.group(1))
    if "The command exited with code 0" in content:
        return 0
    return None


def read_file_safe(path: Path) -> Optional[str]:
    """Safely read text file with utf-8 encoding."""
    if not path.exists() or not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def codex_sessions_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser() / "sessions"


def find_codex_transcript(conversation_id: Optional[str], source: Optional[str] = None) -> Optional[Path]:
    if source:
        path = Path(source).expanduser().resolve()
        return path if path.is_file() else None
    root = codex_sessions_dir()
    if not root.is_dir():
        return None
    files = root.rglob("*.jsonl")
    if conversation_id:
        return next((p for p in files if conversation_id in p.stem), None)
    return max(files, key=lambda p: p.stat().st_mtime, default=None)


def parse_codex_transcript(path: Path, include_subagents: bool = True) -> Dict[str, Any]:
    """Read Codex rollout JSONL. Only exported content present in the log is included."""
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    session = next((r.get("payload", {}) for r in records if r.get("type") == "session_meta"), {})
    cid = session.get("id") or path.stem.rsplit("-", 1)[-1]
    dialogue, commands, timeline, calls = [], [], [], {}
    for index, record in enumerate(records):
        if record.get("type") != "response_item":
            continue
        item = record.get("payload", {})
        kind = item.get("type")
        stamp = record.get("timestamp", "")
        if kind == "message" and item.get("role") in ("user", "assistant"):
            content = "\n".join(str(part.get("text", "")) for part in item.get("content", []) if part.get("type") in ("input_text", "output_text"))
            role = item["role"]
            dialogue.append({"turn": len(dialogue) + 1, "step_index": index, "speaker": role, "timestamp": stamp, "content": content, "response": content if role == "assistant" else "", "thinking": "", "tool_calls": []})
            timeline.append({"timestamp": stamp, "event_type": "user_message" if role == "user" else "assistant_response", "content": content, "response": content})
        elif kind in ("function_call", "custom_tool_call"):
            name = item.get("name", "")
            raw_args = item.get("arguments", item.get("input", ""))
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except (ValueError, TypeError):
                args = {"raw": raw_args}
            call_id = item.get("call_id", "")
            calls[call_id] = {"name": name, "args": args, "timestamp": stamp, "step_index": index}
            if dialogue and dialogue[-1]["speaker"] == "assistant":
                dialogue[-1]["tool_calls"].append({"name": name, "args": args})
        elif kind in ("function_call_output", "custom_tool_call_output"):
            call = calls.get(item.get("call_id"), {})
            if call.get("name") in ("exec_command", "functions.exec_command"):
                args = call.get("args", {})
                output = item.get("output", "")
                commands.append({"step_index": call.get("step_index"), "timestamp": call.get("timestamp", ""), "command": args.get("cmd", ""), "cwd": args.get("workdir", session.get("cwd", "")), "exit_code": parse_exit_code(str(output)), "output": output})
                timeline.append({"timestamp": stamp, "event_type": "command_execution", "command": args.get("cmd", ""), "exit_code": commands[-1]["exit_code"]})
    return {"conversation_id": cid, "metadata": {"conversation_id": cid, "provider": "codex", "transcript_source": str(path), "start_time": records[0].get("timestamp", "") if records else "", "end_time": records[-1].get("timestamp", "") if records else "", "total_steps": len(records), "total_dialogue_turns": len(dialogue), "total_commands_run": len(commands), "total_tasks": 0, "total_subagents": 0}, "dialogue": dialogue, "command_history": commands, "task_history": [], "subagents": [], "timeline": timeline}
class TranscriptParser:
    """Parses Antigravity transcript files for a specific conversation."""

    def __init__(self, brain_dir: Path, conversation_id: str, visited_ids: Optional[set] = None):
        self.brain_dir = brain_dir
        self.conversation_id = conversation_id
        self.conv_dir = brain_dir / conversation_id
        self.logs_dir = self.conv_dir / ".system_generated" / "logs"
        self.steps_dir = self.conv_dir / ".system_generated" / "steps"
        self.tasks_dir = self.conv_dir / ".system_generated" / "tasks"
        self.visited_ids = visited_ids if visited_ids is not None else set()
        self.visited_ids.add(conversation_id)

    def locate_transcript_file(self) -> Optional[Path]:
        """Locate transcript_full.jsonl or transcript.jsonl."""
        full_p = self.logs_dir / "transcript_full.jsonl"
        if full_p.exists() and full_p.stat().st_size > 0:
            return full_p
        compact_p = self.logs_dir / "transcript.jsonl"
        if compact_p.exists() and compact_p.stat().st_size > 0:
            return compact_p
        return None

    def get_full_step_output(self, step_index: int, default_content: str) -> str:
        """Fetch step output from step folder if content was truncated."""
        step_out = self.steps_dir / str(step_index) / "output.txt"
        if step_out.exists():
            full_text = read_file_safe(step_out)
            if full_text:
                return full_text
        return default_content

    def parse(self) -> Dict[str, Any]:
        """Parse the conversation transcript into structured dictionary."""
        transcript_file = self.locate_transcript_file()
        if not transcript_file:
            return {
                "conversation_id": self.conversation_id,
                "error": f"Transcript file not found in {self.logs_dir}",
                "steps": [],
                "dialogue": [],
                "command_history": [],
                "task_history": [],
                "subagents": []
            }

        steps: List[Dict[str, Any]] = []
        with open(transcript_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    step_data = json.loads(line)
                    steps.append(step_data)
                except json.JSONDecodeError:
                    continue

        dialogue: List[Dict[str, Any]] = []
        command_history: List[Dict[str, Any]] = []
        task_history: List[Dict[str, Any]] = []
        subagents_invocations: List[Dict[str, Any]] = []
        timeline: List[Dict[str, Any]] = []

        total_steps = len(steps)
        start_time = steps[0].get("created_at") if steps else None
        end_time = steps[-1].get("created_at") if steps else None

        # Build mapping of tool calls to outputs
        # Usually step i is PLANNER_RESPONSE with tool_calls, step i+1 is GENERIC / tool response
        tool_outputs_map: Dict[int, Dict[str, Any]] = {}
        for s in steps:
            s_type = s.get("type", "")
            s_source = s.get("source", "")
            s_idx = s.get("step_index", -1)
            if s_type != "PLANNER_RESPONSE" and s_type != "USER_INPUT":
                tool_outputs_map[s_idx] = s

        current_turn = 0
        active_subagent_ids: List[Dict[str, Any]] = []

        for i, step in enumerate(steps):
            step_idx = step.get("step_index", i)
            source = step.get("source", "")
            step_type = step.get("type", "")
            created_at = step.get("created_at", "")
            status = step.get("status", "DONE")
            content = step.get("content", "")
            thinking = step.get("thinking", "")
            tool_calls = step.get("tool_calls", [])

            # Check if output is truncated and can be retrieved from steps folder
            if "truncated_fields" in step and "content" in step["truncated_fields"]:
                content = self.get_full_step_output(step_idx, content)

            # 1. USER_INPUT
            if step_type == "USER_INPUT" or source == "USER_EXPLICIT":
                current_turn += 1
                clean_req, meta = clean_user_content(content)
                item = {
                    "turn": current_turn,
                    "step_index": step_idx,
                    "speaker": "user",
                    "timestamp": created_at,
                    "content": clean_req,
                    "raw_content": content,
                    "metadata": meta
                }
                dialogue.append(item)
                timeline.append({
                    "event_type": "user_message",
                    "step_index": step_idx,
                    "timestamp": created_at,
                    "content": clean_req
                })

            # 2. PLANNER_RESPONSE (Assistant Turn)
            elif step_type == "PLANNER_RESPONSE":
                # Find matching output for tool_calls if any
                tools_executed: List[Dict[str, Any]] = []
                for tc in tool_calls:
                    tc_name = tc.get("name", "")
                    tc_args = tc.get("args", {})
                    # Look ahead for matching tool execution result
                    exec_output = ""
                    exec_status = "UNKNOWN"
                    exec_step_idx = None
                    if (step_idx + 1) in tool_outputs_map:
                        out_step = tool_outputs_map[step_idx + 1]
                        exec_output = out_step.get("content", "")
                        exec_status = out_step.get("status", "DONE")
                        exec_step_idx = out_step.get("step_index")
                        if "truncated_fields" in out_step and "content" in out_step["truncated_fields"]:
                            exec_output = self.get_full_step_output(exec_step_idx, exec_output)

                    tool_exec_info = {
                        "name": tc_name,
                        "args": tc_args,
                        "output_step_index": exec_step_idx,
                        "status": exec_status,
                        "output": exec_output
                    }
                    tools_executed.append(tool_exec_info)

                    # Extract run_command
                    if tc_name == "run_command":
                        cmd_line = tc_args.get("CommandLine", "")
                        cwd = tc_args.get("Cwd", "")
                        is_daemon = tc_args.get("IsDaemon", False)
                        exit_code = parse_exit_code(exec_output)
                        cmd_info = {
                            "step_index": step_idx,
                            "output_step_index": exec_step_idx,
                            "timestamp": created_at,
                            "command": cmd_line,
                            "cwd": cwd,
                            "is_daemon": is_daemon,
                            "status": exec_status,
                            "exit_code": exit_code,
                            "output": exec_output
                        }
                        command_history.append(cmd_info)
                        timeline.append({
                            "event_type": "command_execution",
                            "step_index": step_idx,
                            "timestamp": created_at,
                            "command": cmd_line,
                            "exit_code": exit_code,
                            "output_preview": exec_output[:300] if exec_output else ""
                        })

                    # Extract schedule / timers / crons
                    elif tc_name == "schedule":
                        duration = tc_args.get("DurationSeconds")
                        cron = tc_args.get("CronExpression")
                        prompt = tc_args.get("Prompt", "")
                        cond = tc_args.get("TimerCondition")
                        # Parse task ID from output
                        task_id_match = re.search(r"task id:\s*([^\s\n]+)", exec_output)
                        task_id = task_id_match.group(1) if task_id_match else None
                        task_info = {
                            "task_id": task_id,
                            "type": "schedule",
                            "step_index": step_idx,
                            "timestamp": created_at,
                            "duration_seconds": duration,
                            "cron_expression": cron,
                            "prompt": prompt,
                            "condition": cond,
                            "output": exec_output
                        }
                        task_history.append(task_info)
                        timeline.append({
                            "event_type": "schedule_task",
                            "step_index": step_idx,
                            "timestamp": created_at,
                            "task_id": task_id,
                            "prompt": prompt
                        })

                    # Extract manage_task
                    elif tc_name == "manage_task":
                        action = tc_args.get("Action", "")
                        task_id = tc_args.get("TaskId", "")
                        task_info = {
                            "task_id": task_id,
                            "type": f"manage_task_{action}",
                            "step_index": step_idx,
                            "timestamp": created_at,
                            "action": action,
                            "output": exec_output
                        }
                        task_history.append(task_info)

                    # Extract invoke_subagent
                    elif tc_name == "invoke_subagent":
                        subagents_list = tc_args.get("Subagents", [])
                        # Extract conversation IDs from exec_output
                        # The output usually contains: "conversationId": "...", "logAbsoluteUri": "..."
                        conv_ids = re.findall(r'"conversationId":\s*"([^"]+)"', exec_output)
                        for sa_idx, sa_spec in enumerate(subagents_list):
                            cid = conv_ids[sa_idx] if sa_idx < len(conv_ids) else None
                            sa_record = {
                                "conversation_id": cid,
                                "type_name": sa_spec.get("TypeName"),
                                "role": sa_spec.get("Role"),
                                "model": sa_spec.get("Model"),
                                "prompt": sa_spec.get("Prompt"),
                                "workspace": sa_spec.get("Workspace"),
                                "invoked_at": created_at,
                                "step_index": step_idx,
                                "raw_output": exec_output
                            }
                            subagents_invocations.append(sa_record)
                            if cid and cid not in [x.get("conversation_id") for x in active_subagent_ids]:
                                active_subagent_ids.append(sa_record)
                            timeline.append({
                                "event_type": "invoke_subagent",
                                "step_index": step_idx,
                                "timestamp": created_at,
                                "role": sa_spec.get("Role"),
                                "type": sa_spec.get("TypeName"),
                                "conversation_id": cid
                            })

                    # Extract send_message to subagents
                    elif tc_name == "send_message":
                        recipient = tc_args.get("Recipient")
                        msg = tc_args.get("Message")
                        timeline.append({
                            "event_type": "send_message",
                            "step_index": step_idx,
                            "timestamp": created_at,
                            "recipient": recipient,
                            "message_preview": msg[:200] if msg else ""
                        })

                # Check if there's textual content for assistant response
                if content or thinking or tools_executed:
                    current_turn += 1
                    dialogue.append({
                        "turn": current_turn,
                        "step_index": step_idx,
                        "speaker": "assistant",
                        "timestamp": created_at,
                        "thinking": thinking,
                        "response": content,
                        "tool_calls": tools_executed
                    })
                    if content:
                        timeline.append({
                            "event_type": "assistant_response",
                            "step_index": step_idx,
                            "timestamp": created_at,
                            "response": content
                        })

            # 3. SYSTEM_MESSAGE (Background task notifications, timer wakeups)
            elif source == "SYSTEM" or step_type == "SYSTEM_MESSAGE":
                timeline.append({
                    "event_type": "system_notification",
                    "step_index": step_idx,
                    "timestamp": created_at,
                    "content": content
                })

        # Enrich task history with log files from tasks/ directory if available
        if self.tasks_dir.exists():
            for task_log in self.tasks_dir.glob("task-*.log"):
                task_name = task_log.stem  # e.g. task-50
                full_task_id = f"{self.conversation_id}/{task_name}"
                matched = next((t for t in task_history if t.get("task_id") in (task_name, full_task_id)), None)
                log_txt = read_file_safe(task_log)
                if matched:
                    matched["log_content"] = log_txt
                    matched["log_path"] = str(task_log)
                else:
                    task_history.append({
                        "task_id": full_task_id,
                        "type": "background_log",
                        "log_path": str(task_log),
                        "log_content": log_txt
                    })

        # Recursively parse subagents
        parsed_subagents: List[Dict[str, Any]] = []
        for sa in active_subagent_ids:
            cid = sa.get("conversation_id")
            if not cid or cid in self.visited_ids:
                continue
            subagent_parser = TranscriptParser(self.brain_dir, cid, self.visited_ids)
            sub_res = subagent_parser.parse()
            parsed_subagents.append({
                "subagent_meta": sa,
                "subagent_data": sub_res
            })

        metadata = {
            "conversation_id": self.conversation_id,
            "transcript_source": str(transcript_file),
            "start_time": start_time,
            "end_time": end_time,
            "total_steps": total_steps,
            "total_dialogue_turns": len(dialogue),
            "total_commands_run": len(command_history),
            "total_tasks": len(task_history),
            "total_subagents": len(parsed_subagents)
        }

        return {
            "conversation_id": self.conversation_id,
            "metadata": metadata,
            "dialogue": dialogue,
            "command_history": command_history,
            "task_history": task_history,
            "subagents": parsed_subagents,
            "timeline": timeline
        }


def format_to_markdown(data: Dict[str, Any], include_thinking: bool = True, include_raw_tools: bool = False) -> str:
    """Format parsed conversation data into a clean, comprehensive Markdown document."""
    meta = data.get("metadata", {})
    conv_id = data.get("conversation_id", "Unknown")
    start_time = meta.get("start_time", "N/A")
    end_time = meta.get("end_time", "N/A")
    total_turns = meta.get("total_dialogue_turns", 0)
    total_cmds = meta.get("total_commands_run", 0)
    total_tasks = meta.get("total_tasks", 0)
    total_subagents = meta.get("total_subagents", 0)

    lines: List[str] = []
    lines.append(f"# 📜 Conversation Transcript & Execution Report")
    lines.append(f"\n> **Conversation ID**: `{conv_id}`  ")
    lines.append(f"> **Exported At**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ")
    lines.append(f"> **Duration**: `{start_time}` &rarr; `{end_time}`\n")

    # Metadata Table
    lines.append("## 📊 Summary Statistics\n")
    lines.append("| Metric | Count |")
    lines.append("| :--- | :--- |")
    lines.append(f"| 💬 Total Dialogue Turns | **{total_turns}** |")
    lines.append(f"| 💻 Terminal Commands Run | **{total_cmds}** |")
    lines.append(f"| ⏱️ Tasks & Schedules | **{total_tasks}** |")
    lines.append(f"| 🤖 Subagents Invoked | **{total_subagents}** |")
    lines.append("")

    # Table of Contents
    lines.append("## 📑 Table of Contents")
    lines.append("- [1. Full Dialogue & Turn History](#1-full-dialogue--turn-history)")
    lines.append("- [2. Terminal Command Execution History](#2-terminal-command-execution-history)")
    lines.append("- [3. Background Tasks & Schedules](#3-background-tasks--schedules)")
    lines.append("- [4. Subagent Operations & Tree](#4-subagent-operations--tree)")
    lines.append("- [5. Chronological Event Timeline](#5-chronological-event-timeline)\n")

    # 1. Dialogue
    lines.append("## 1. Full Dialogue & Turn History\n")
    for turn in data.get("dialogue", []):
        speaker = turn.get("speaker", "")
        timestamp = turn.get("timestamp", "")
        content = turn.get("content", "")
        thinking = turn.get("thinking", "")
        tools = turn.get("tool_calls", [])
        step_idx = turn.get("step_index", "")

        if speaker == "user":
            lines.append(f"### 👤 User (Step {step_idx}) — `{timestamp}`")
            lines.append(f"\n{content}\n")
        else:
            lines.append(f"### 🤖 Assistant (Step {step_idx}) — `{timestamp}`\n")
            if include_thinking and thinking:
                lines.append("<details>")
                lines.append("<summary><b>🧠 Model Thinking / Chain of Thought</b></summary>\n")
                lines.append(f"```text\n{thinking.strip()}\n```\n")
                lines.append("</details>\n")

            if tools:
                lines.append("<details>")
                lines.append(f"<summary><b>🛠️ Tools Executed ({len(tools)} call{'s' if len(tools)>1 else ''})</b></summary>\n")
                for t in tools:
                    t_name = t.get("name")
                    t_args = json.dumps(t.get("args", {}), indent=2, ensure_ascii=False)
                    lines.append(f"- **Tool**: `{t_name}`")
                    lines.append(f"  ```json\n{t_args}\n  ```")
                lines.append("</details>\n")

            if content:
                lines.append(f"{content}\n")

        lines.append("---\n")

    # 2. Command Execution History
    lines.append("## 2. Terminal Command Execution History\n")
    commands = data.get("command_history", [])
    if not commands:
        lines.append("_No terminal commands (`run_command`) were executed in this conversation._\n")
    else:
        lines.append(f"Total commands executed: **{len(commands)}**\n")
        lines.append("| # | Timestamp | Working Directory | Command | Exit Code |")
        lines.append("| :- | :--- | :--- | :--- | :--- |")
        for idx, cmd in enumerate(commands, 1):
            ts = cmd.get("timestamp", "")
            cwd = cmd.get("cwd", "")
            c_text = cmd.get("command", "").replace("\n", " ")
            if len(c_text) > 60:
                c_text = c_text[:57] + "..."
            code = cmd.get("exit_code")
            code_badge = f"`{code}`" if code is not None else "`Async/Task`"
            lines.append(f"| {idx} | `{ts}` | `{cwd}` | `{c_text}` | {code_badge} |")
        lines.append("")

        lines.append("### Detailed Command Logs\n")
        for idx, cmd in enumerate(commands, 1):
            lines.append(f"#### Command #{idx} (Step {cmd.get('step_index')})")
            lines.append(f"- **Working Directory**: `{cmd.get('cwd')}`")
            lines.append(f"- **Timestamp**: `{cmd.get('timestamp')}`")
            lines.append(f"- **Exit Code**: `{cmd.get('exit_code')}`")
            lines.append(f"\n```bash\n{cmd.get('command')}\n```\n")
            out = cmd.get("output", "").strip()
            if out:
                lines.append("<details>")
                lines.append("<summary><b>Command Output Log</b></summary>\n")
                lines.append(f"```text\n{out}\n```\n")
                lines.append("</details>\n")
            lines.append("")

    # 3. Tasks & Schedules
    lines.append("## 3. Background Tasks & Schedules\n")
    tasks = data.get("task_history", [])
    if not tasks:
        lines.append("_No background tasks or schedules recorded._\n")
    else:
        for idx, task in enumerate(tasks, 1):
            t_id = task.get("task_id", f"Task-{idx}")
            t_type = task.get("type", "task")
            lines.append(f"### ⏱️ Task: `{t_id}` ({t_type})")
            if "prompt" in task:
                lines.append(f"- **Prompt**: {task.get('prompt')}")
            if "duration_seconds" in task and task.get("duration_seconds"):
                lines.append(f"- **Duration**: {task.get('duration_seconds')}s")
            if "cron_expression" in task and task.get("cron_expression"):
                lines.append(f"- **Cron Expression**: `{task.get('cron_expression')}`")
            log_c = task.get("log_content")
            if log_c:
                lines.append("<details>")
                lines.append("<summary><b>Task Execution Log</b></summary>\n")
                lines.append(f"```text\n{log_c.strip()}\n```\n")
                lines.append("</details>\n")
            lines.append("")

    # 4. Subagents
    lines.append("## 4. Subagent Operations & Tree\n")
    subagents = data.get("subagents", [])
    if not subagents:
        lines.append("_No subagents (`invoke_subagent`) were invoked in this conversation._\n")
    else:
        lines.append(f"Total subagents spawned: **{len(subagents)}**\n")
        for sa_wrap in subagents:
            sa_meta = sa_wrap.get("subagent_meta", {})
            sa_data = sa_wrap.get("subagent_data", {})
            sa_id = sa_meta.get("conversation_id", "Unknown")
            role = sa_meta.get("role", "Subagent")
            type_name = sa_meta.get("type_name", "subagent")
            prompt = sa_meta.get("prompt", "")

            lines.append(f"### 🤖 Subagent: **{role}** (`{type_name}`)")
            lines.append(f"- **Subagent Conversation ID**: `{sa_id}`")
            lines.append(f"- **Model**: `{sa_meta.get('model')}`")
            lines.append(f"- **Invoked At**: `{sa_meta.get('invoked_at')}`")
            lines.append(f"\n**Assigned Prompt / Objective**:\n")
            lines.append(f"> {prompt.replace(chr(10), chr(10) + '> ')}\n")

            sa_dialogue = sa_data.get("dialogue", [])
            sa_commands = sa_data.get("command_history", [])

            lines.append(f"**Execution Summary inside Subagent**:")
            lines.append(f"- Turns: **{len(sa_dialogue)}**")
            lines.append(f"- Commands run: **{len(sa_commands)}**\n")

            if sa_commands:
                lines.append("<details>")
                lines.append(f"<summary><b>💻 Subagent Commands Run ({len(sa_commands)})</b></summary>\n")
                for c_idx, scmd in enumerate(sa_commands, 1):
                    lines.append(f"- **#{c_idx}** `{scmd.get('command')}` (Exit: `{scmd.get('exit_code')}`)")
                lines.append("</details>\n")

            if sa_dialogue:
                lines.append("<details>")
                lines.append(f"<summary><b>💬 Subagent Internal Dialogue Transcript ({len(sa_dialogue)} turns)</b></summary>\n")
                for s_turn in sa_dialogue:
                    spk = s_turn.get("speaker")
                    s_content = s_turn.get("content", "")
                    s_thinking = s_turn.get("thinking", "")
                    s_ts = s_turn.get("timestamp", "")
                    lines.append(f"##### {spk.upper()} (`{s_ts}`)")
                    if s_thinking and include_thinking:
                        lines.append(f"```text\n{s_thinking[:400]}...\n```")
                    if s_content:
                        lines.append(f"{s_content}\n")
                lines.append("</details>\n")

            lines.append("---\n")

    # 5. Timeline
    lines.append("## 5. Chronological Event Timeline\n")
    timeline = data.get("timeline", [])
    if timeline:
        lines.append("| Time | Event Type | Details |")
        lines.append("| :--- | :--- | :--- |")
        for item in timeline:
            ts = item.get("timestamp", "")
            etype = item.get("event_type", "")
            details = ""
            if etype == "user_message":
                details = f"User Request: {item.get('content', '')[:60]}..."
            elif etype == "command_execution":
                details = f"Command: `{item.get('command', '')[:50]}` (Exit: `{item.get('exit_code')}`)"
            elif etype == "invoke_subagent":
                details = f"Spawned Subagent: **{item.get('role')}** (`{item.get('type')}`)"
            elif etype == "schedule_task":
                details = f"Scheduled: {item.get('prompt', '')[:50]}"
            elif etype == "assistant_response":
                details = f"Assistant Response: {item.get('response', '')[:60]}..."
            elif etype == "system_notification":
                details = f"System: {item.get('content', '')[:60]}..."
            lines.append(f"| `{ts}` | `{etype}` | {details} |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export Antigravity or Codex conversations to Markdown and JSON."
    )
    parser.add_argument(
        "-c", "--conversation-id",
        type=str,
        default=None,
        help="Conversation ID to export. Defaults to current Codex thread or latest Antigravity conversation."
    )
    parser.add_argument(
        "-b", "--brain-dir",
        type=str,
        default=None,
        help="Custom path to Antigravity brain directory."
    )
    parser.add_argument("--agent", choices=["auto", "antigravity", "codex"], default="auto", help="Transcript adapter. Auto detects the current agent.")
    parser.add_argument("--source", help="Explicit Codex rollout JSONL file.")
    parser.add_argument(
        "-f", "--format",
        choices=["md", "json", "all"],
        default="all",
        help="Export format: 'md' (Markdown), 'json' (JSON), or 'all' (both). Default: 'all'."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (without extension if format=all) or target directory. Defaults to ./.scratch/export_<date>_<conv_id>/."
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Exclude model thinking / chain-of-thought from the Markdown export."
    )
    parser.add_argument(
        "--no-subagents",
        action="store_true",
        help="Do not recursively parse subagent transcripts."
    )

    args = parser.parse_args()

    agent = args.agent
    if agent == "auto":
        agent = "codex" if args.source or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "antigravity"
    if agent == "codex":
        requested_id = args.conversation_id or (os.environ.get("CODEX_THREAD_ID") if args.agent == "auto" else None)
        transcript = find_codex_transcript(requested_id, args.source)
        if not transcript:
            print("[-] Error: Codex transcript not found. Pass --source FILE or -c THREAD_ID.", file=sys.stderr)
            return 1
        parsed_data = parse_codex_transcript(transcript, include_subagents=not args.no_subagents)
        conv_id = parsed_data["conversation_id"]
    else:
        brain_dir = Path(args.brain_dir).expanduser().resolve() if args.brain_dir else get_default_brain_dir()
        if not brain_dir.exists():
            print(f"[-] Error: Brain directory does not exist: {brain_dir}", file=sys.stderr)
            return 1
        conv_id = args.conversation_id or find_latest_conversation(brain_dir)
        if not conv_id or not (brain_dir / conv_id).exists():
            print(f"[-] Error: Antigravity conversation not found in {brain_dir}", file=sys.stderr)
            return 1
        parsed_data = TranscriptParser(brain_dir, conv_id).parse()
    print(f"[+] Adapter: {agent}; conversation: {conv_id}")

    if not args.no_subagents:
        subagent_count = len(parsed_data.get("subagents", []))
        if subagent_count > 0:
            print(f"[+] Successfully extracted {subagent_count} subagent transcript(s).")

    # Determine output file path
    now_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if args.output:
        out_path = Path(args.output).resolve()
        if out_path.is_dir() or args.output.endswith(("/", "\\")):
            out_path.mkdir(parents=True, exist_ok=True)
            base_filename = out_path / f"conversation_{conv_id[:8]}_{now_str}"
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if out_path.suffix in (".md", ".json"):
                base_filename = out_path.with_suffix("")
            else:
                base_filename = out_path
    else:
        # Default session directory inside ./.scratch/
        scratch_dir = Path("./.scratch") / f"{datetime.now().strftime('%Y-%m-%d')}_export-conversation_{conv_id[:8]}"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        base_filename = scratch_dir / f"conversation_{conv_id[:8]}_{now_str}"

    outputs_created: List[Path] = []

    # Export JSON
    if args.format in ("json", "all"):
        json_file = base_filename.with_suffix(".json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        outputs_created.append(json_file)
        print(f"[+] Exported JSON to: {json_file}")

    # Export Markdown
    if args.format in ("md", "all"):
        md_file = base_filename.with_suffix(".md")
        md_content = format_to_markdown(parsed_data, include_thinking=not args.no_thinking)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        outputs_created.append(md_file)
        print(f"[+] Exported Markdown to: {md_file}")

    print("\n[+] Export Summary:")
    meta = parsed_data.get("metadata", {})
    print(f"    - Turns: {meta.get('total_dialogue_turns', 0)}")
    print(f"    - Commands: {meta.get('total_commands_run', 0)}")
    print(f"    - Tasks: {meta.get('total_tasks', 0)}")
    print(f"    - Subagents: {meta.get('total_subagents', 0)}")
    print(f"    - Output Files: {[str(p) for p in outputs_created]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
