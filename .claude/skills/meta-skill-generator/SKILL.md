---
name: meta-skill-generator
description: Converts AI skills, agent personas, workflows, and instructions between Claude Skills, Hermes Skills, Cursor Rules, Roo Modes, Cline Modes, Gemini Gems, Copilot Instructions, OpenAI GPT Instructions, and other agent frameworks.
---

# Meta Skill Generator

## Purpose

Act as a universal skill conversion engine.

Analyze any AI skill, workflow, persona, instruction set, or agent configuration.

Transform it into one or more target formats while preserving:

- Purpose
- Capabilities
- Constraints
- Workflows
- Outputs
- Validation logic

---

# Supported Inputs

## Claude Skills

Examples:

- SKILL.md
- Complete skill folders

---

## Hermes Skills

Examples:

- SKILL.md
- SOUL.md
- Supporting files

---

## Cursor Rules

Examples:

- .cursor/rules/*.mdc
- project rules

---

## Roo Code Modes

Examples:

- mode definitions
- mode prompts

---

## Cline Modes

Examples:

- system prompts
- mode prompts

---

## Gemini Gems

Examples:

- Gem instructions
- Gem configurations

---

## GitHub Copilot Instructions

Examples:

- copilot-instructions.md

---

## OpenAI GPT Instructions

Examples:

- GPT system prompts
- Custom GPT configurations

---

# Canonical Skill Model

Convert all incoming formats into the following internal model.

## Identity

Name

Description

Purpose

Category

Tags

---

## Activation

When should the skill activate?

Examples:

- code audit
- architecture review
- project generation
- testing

---

## Capabilities

List all supported capabilities.

---

## Inputs

Expected user inputs.

---

## Workflows

Step-by-step procedures.

---

## Constraints

Rules that must not be violated.

---

## Deliverables

Expected outputs.

---

## Validation

Completion criteria.

---

## Examples

Usage examples.

---

## Supporting Assets

Templates

References

Scripts

Examples

Checklists

---

# Conversion Process

## Phase 1

Identify source format.

---

## Phase 2

Extract canonical model.

---

## Phase 3

Normalize:

- persona
- workflow
- constraints
- outputs

---

## Phase 4

Generate target format.

---

# Supported Outputs

## Claude Skill

Generate:

```text
skill/
└── SKILL.md
```

Include:

- frontmatter
- description
- workflows
- examples

---

## Hermes Skill

Generate:

```text
skill/
├── SKILL.md
├── templates/
├── references/
└── examples/
```

Include:

- activation criteria
- deliverables
- success criteria
- failure conditions

Extract persona into SOUL.md recommendations.

---

## Cursor Rule

Generate:

```text
.cursor/rules/
└── skill-name.mdc
```

Include:

- scope
- triggers
- instructions

---

## Roo Mode

Generate complete mode configuration.

---

## Cline Mode

Generate complete mode configuration.

---

## Gemini Gem

Generate:

- Gem Name
- Description
- Instructions
- Suggested starters

---

## GitHub Copilot Instructions

Generate:

```text
.github/
└── copilot-instructions.md
```

---

## OpenAI GPT

Generate:

- System Prompt
- Conversation Starters
- Knowledge Recommendations

---

# Cross-Framework Enhancements

When generating outputs:

Enhance with:

## Activation Criteria

Explicit activation conditions.

---

## Deliverables

Expected outputs.

---

## Validation

Completion checklist.

---

## Failure Conditions

Clarification requirements.

---

## Examples

Practical usage examples.

---

# Persona Handling

If persona content exists:

Extract into:

```markdown
# Persona
```

Separate from workflow logic.

Frameworks supporting personas:

- Hermes
- GPTs
- Gemini Gems
- Roo Modes
- Cline Modes

Frameworks focused on procedures:

- Claude Skills
- Cursor Rules
- Copilot Instructions

Adapt accordingly.

---

# Output Requirements

Always generate:

## Conversion Summary

Detected source format.

Detected capabilities.

Enhancements applied.

Potential compatibility issues.

---

## Canonical Skill Model

Show normalized representation.

---

## Generated Target Format

Provide complete output.

---

## Supporting Files

Generate all required files.

---

## Recommendations

Suggested improvements for the target framework.

---

# Quality Requirements

Generated outputs must:

- Be production-ready.
- Be framework-compliant.
- Preserve original intent.
- Preserve workflows.
- Preserve constraints.
- Improve activation reliability.
- Improve validation.
- Improve maintainability.

Never generate incomplete conversions when sufficient information exists.