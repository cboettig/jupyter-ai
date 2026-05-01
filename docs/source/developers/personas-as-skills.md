# Personas as Skills

*A note on how the per-chat harness binding work in this fork sits
inside the original Personas vision in `jupyter-ai-persona-manager`,
and a friendly suggestion for how that vision might align with where
the broader open agent ecosystem is converging.*

This is companion reading for [issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558)
and the [ACP bridge design spec](../../superpowers/specs/2026-04-28-acp-bridge-design.md).
It's about *concepts*, not code — the goal is to put names on three
things that have been quietly co-existing inside "I'm chatting with an
AI" and to suggest where each belongs.

## Why this matters

The Personas surface in `jupyter-ai-persona-manager` was a strong
design call. It frames the right thing: the user — and especially the
*expert user* — should be able to shape a conversation with a
domain-specific bundle of context, identity, and tools, *per chat*,
without that shaping leaking elsewhere. That's exactly what scientists
need to bring their accumulated expertise into AI-assisted work
without surrendering it to whatever generic assistant a vendor ships.
The Personas vision makes that contribution surface explicit.

This document doesn't argue against Personas. It argues that the
*format* for declaring one — what a persona physically *is* — has,
since the persona-manager was designed, converged on an open standard
in the broader ecosystem (Agent Client Protocol / ACP). Aligning with that standard
makes the expert-user contribution surface lower-friction *and* portable beyond Jupyter,
and that combination is what determines whether a community of expert-authored personas
actually accumulates.

## Three axes that aren't always one thing

Inside any "I'm chatting with an AI" interaction there are at least
three independent axes:

| Axis | Examples |
|---|---|
| **Model** — which LLM is doing inference | Sonnet 4.6, Haiku 4.5, GPT-5.5, Gemini 3 Pro, … |
| **Harness** — which agent runtime mediates tool use, file I/O, MCP, slash dispatch, multi-turn loops, sub-agents | Claude Code (`claude-agent-acp`), OpenCode, Codex, Goose, Gemini-CLI, Cursor, … |
| **Persona** — what bundle of *context* the user has adopted for this conversation | "Senior data scientist", "Strict code reviewer", "Field biologist studying salmon", … |

These three are orthogonal. You can want the same persona on a
different model. You can want it on a different harness. You can want
it across totally different chat surfaces (Jupyter, terminal, IDE).
Independent selection of all three is what gives the user real agency.

The trouble starts when an interface conflates two of them. Two
specific conflations worth naming:

1. **Persona ↔ harness.** "`@claude` is a persona" implicitly equates
   the harness (`claude-agent-acp`) with a persona identity. Switching
   harnesses means abandoning the persona; defining a persona requires
   knowing which harness you're authoring it for.

2. **Persona ↔ model.** "My data-scientist persona uses Sonnet" bakes
   model selection into the persona definition. The same persona on a
   different model is now a different persona, and changing models —
   for cost or capability reasons — forces a redefinition.

The per-chat ACP harness binding in this fork separates axis 1 from
axis 3 at the chat layer: a chat is bound to one harness, and the
harness's models/modes/skills are surfaced as separate selectors. But
it doesn't, on its own, say what a *persona* should be — it just stops
calling the harness one.

## What is a Persona, really?

Our proposal is to have a more robust definition of a persona; instead of a thing you
can `@`, a persona has a specific scope of responsibility.

Strip away the implementation, and a persona is a **bundle of context
loaded into a conversation**:

- A system prompt (the "voice" / behavior).
- Domain rules ("when working with geospatial data, prefer GeoParquet
  and explicit CRS tags").
- Optional tool wiring (MCP servers, allowed shell commands, file
  scopes).
- Optional bundled scripts the persona invokes when relevant.
- Optional reference material (templates, examples, schemas).
- Metadata about *when* the persona applies.

That's what a persona *is*. The Python class structure, entry-point
registration, and mention-name routing in the current implementation
are plumbing for *delivering* the bundle, not what the bundle is.

## Skills: an open standard for exactly this

[**agentskills.io**](https://agentskills.io/home) defines an open
standard called Agent Skills that describes precisely the bundle
above. A Skill is a folder:

```
my-skill/
├── SKILL.md          # required: metadata + instructions
├── scripts/          # optional: executable code
├── references/       # optional: documentation, examples
├── assets/           # optional: templates, resources
└── …                 # any additional files or directories
```

`SKILL.md` carries YAML frontmatter (`name`, `description`, when-to-use)
and instructions. Bundled `scripts/` are executable code the skill can
invoke. The format includes a *progressive-disclosure* loading model —
agents see name and description at startup, load full instructions on
activation, and execute bundled code on demand — so a workspace can
hold many skills with a small standing context footprint.

This is not a markdown-only minimum-viable spec. Skills are
fully expressive: code, tools, MCP wiring, bundled assets, references —
the same surface a richly-implemented persona would want.

The Skills standard was originally developed at Anthropic, **released
as an open standard, and is now adopted across a wide cross-section of
the agent ecosystem**: Junie / JetBrains, Gemini CLI / Google,
OpenCode, OpenHands, Mux, Cursor, Amp, Letta, Goose / Block, GitHub
Copilot, VS Code / Microsoft, Codex / OpenAI, Spring AI, Mistral
Vibe, Roo Code, Kiro, Snowflake Cortex Code — and many more. Skills
authored for one tool work in any other. (Source: [agentskills.io
client showcase](https://agentskills.io/home).)

## What this means in plain terms

If a persona is a bundle of context, and Skills are an open standard
for bundles of context, then in the simplest case a **persona is a
skill**. A scientist who wants to encode their domain expertise as a
Jupyter persona can:

```
~/.config/agentskills/salmon-ecology/
├── SKILL.md
├── references/study-protocols.md
└── scripts/load_telemetry.py
```

…and that bundle now works as their `salmon-ecology` persona in
Jupyter AI, in their terminal, in their editor, in any
skills-compatible client. They didn't write a Python package. They
didn't import `BasePersona`. They didn't think about entry points.
They wrote the same thing they'd have written anywhere, in the format
the rest of the open ecosystem already uses.

## How `BasePersona` relates

`BasePersona` in `jupyter-ai-persona-manager` is, in effect, a
local-only restatement of the same idea — "give me a context bundle
the chat can adopt" — with a Python-class-and-entry-point packaging
step layered on top, and no shared format with the broader ecosystem.

That's not a knock on `BasePersona`'s design. It predates the
convergence of the Skills standard and was a sensible choice at its
time. But its packaging requirements have a real cost:

- Authoring a persona requires Python coding and packaging knowledge.
- Personas can't be shared across chat surfaces — your jupyter-ai
  persona doesn't work in your terminal, and vice versa.
- Persona libraries don't pool with the broader community; everyone
  invents their own.

For the *common* case of "I want my AI assistant to be a senior
domain expert in topic X for this chat," writing a Python class is
considerable friction with no benefit, and the result doesn't compose
with anything. Aligning the format with Skills removes the friction
*and* the lock-in in one step.

## The naming problem we should call out

Discussions about Personas keep getting tangled because the word is
quietly being used for two genuinely different things:

1. **Lightweight inline persona.** "For this conversation, talk like
   a senior data scientist. Use these references. Have these tools
   available." Loaded into the current chat's context.

2. **Heavyweight isolated specialist.** "Send this sub-task to a
   sqlAgent that runs in its own session, with its own conversation
   history, and only returns a summary." A separate worker
   conversation that the main chat spawns and consumes.

These solve different problems. The first is about user-adopted
context shaping (the Personas vision, narrowly). The second is about
multi-agent orchestration — a separate, harder design space.

Calling both "Personas" obscures the choice. The Skills standard
covers the first cleanly. The second is a different question and
belongs in a different layer (see next section). When this essay
talks about "Personas as Skills," it means the *first* sense. The
second deserves its own name and its own proposal.

## On isolation: the legitimate concern, and why ACP isn't the layer

There's a real tension here, and skipping past it would be
unconvincing. Defenders of `Persona = ACP-session-per-class` will
correctly point out that giving each persona its own ACP session
delivers context isolation: the persona's reasoning, tool calls, and
internal state don't pollute the main chat. That isolation is
sometimes genuinely valuable.

The argument here isn't "isolation doesn't matter." It's that ACP is
the wrong layer to provide it, for three reasons:

1. **Harnesses already provide intra-harness isolation, and they're
   improving fast.** Claude Code's Task tool, OpenCode's sub-agents,
   Goose's worktree-per-agent, Mux's parallel-isolated-workspace
   model, and many others — every modern harness has its own
   sub-agent / sub-session abstraction. Building a parallel one at
   the ACP-client layer duplicates work the harnesses are already
   doing better than a generic client could.

2. **ACP is intentionally 1:1.** ACP defines a single client ↔ agent
   conversation. Multi-agent orchestration is a layer *above* ACP, by
   design. Trying to make the ACP-client layer responsible for
   isolation would mean pushing multi-agent semantics into a protocol
   that wasn't built for it.

3. **`Persona = ACP-session-per-Python-class` doesn't actually deliver
   isolation as an authoring affordance.** What it delivers is "one
   Python package per system-prompt-plus-harness combination." Two
   variants of Claude Code with different system prompts? Two Python
   packages. Same persona in Claude Code *and* OpenCode? Four. The
   user wanted isolation; what they got was a packaging requirement.
   The isolation, when it happens, is incidental to the packaging
   requirement, not orthogonal to it.

For genuinely cross-harness orchestration — "I want a SQL specialist
running in claude-agent-acp and a spatial specialist running in
opencode in the same chat" — the right answer is almost certainly
*not* "make every Jupyter AI client speak that protocol natively."
It's an emerging-standards problem, with [Google's A2A
(Agent-to-Agent)](https://google.github.io/A2A/) and similar
multi-agent protocols starting to settle the design. Jupyter is
better served by *waiting* for that standard to mature and then
adopting it as it adopted ACP, than by inventing a Jupyter-specific
mashup now.

A reasonable position, then:

- The hello-world persona — what 90% of users want, and what makes
  the expert-contribution flywheel turn — should be a Skill. Easy to
  author. Portable. No Python required.
- Full-isolation specialists — the 10% case that genuinely needs a
  separate session — *should* be high-friction. That's the right
  level of friction for a feature with that much overhead. But it
  shouldn't be the only path, and it shouldn't be conflated with
  authoring a context bundle.
- The path between "I want a different system prompt" and "I want a
  separate isolated agent" should be the harness's sub-agent system,
  invoked from a skill — not a separate Python package per
  combination of intent and harness.

## What the bridge actually does today

This fork's bridge gives you the substrate for the reframe even
without any further upstream change:

- It stops calling the harness a persona. Each chat is bound to one
  harness via the augmented `+ New chat` dialog; harness selection is
  independent of model and mode selection.
- It surfaces the bound harness's *available skills* as slash-command
  completions in the chat input — read directly from the ACP
  `AvailableCommandsUpdate` event the harness emits.
- It forwards `/<skill-name>` invocations through to the harness,
  whose own Skills loader handles the rest (including any bundled
  scripts, MCP wiring, references — all of it, per the Skills spec).

So if a user has a skill folder on disk in any of the standard
locations the Skills spec recognizes, and they're in a Jupyter AI
chat bound to any skills-supporting harness, they can already type
`/<skill-name>` and the persona experience works. No
Jupyter-specific persona registration is required. The bridge stays
out of the way.

## A friendly invitation

This is a sketch of a direction, not a pull request. The Personas
vision in `jupyter-ai-persona-manager` is a real design contribution
and addresses something most AI tools currently miss — the
expert-user contribution surface. What's changed since the persona
system was authored is that the rest of the open agent ecosystem has
converged on standards (ACP for the wire, Skills for the
context-bundle format, MCP for tool/resource exposure) that solve
adjacent problems with broad multi-vendor adoption.

Aligning with those standards — especially for the common case where
alignment is essentially free — turns the Personas vision from "the
way Jupyter AI does this thing" into "the way Jupyter AI participates
in how the open ecosystem does this thing." The expert-user surface
gets *wider* (any skills-compatible tool can host a Jupyter-authored
persona), more *durable* (a persona library survives Jupyter version
churn and the rise/fall of any single tool), and more *generative*
(Jupyter contributors and ecosystem contributors share one library
rather than maintaining parallel ones).

The bridge in this fork is a working artifact arguing the case. It
doesn't need to be merged as-is or even at all to make the point —
the point is the framing, and the framing is the conversation.
