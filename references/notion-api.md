# Notion REST API Reference

Source: [Notion API Reference](https://developers.notion.com/reference)

---

## Authentication

Internal integration token (single workspace). Get from: **notion.so → Settings → Connections → Develop or manage integrations**

```
Authorization: Bearer {NOTION_TOKEN}
Notion-Version: 2026-03-11
Content-Type: application/json
```

**Important:** Pages/databases must be explicitly shared with your integration or it gets 404.
To share: open page in Notion → `...` menu → Connections → select your integration.

---

## Base URL

```
https://api.notion.com/v1/
```

---

## Rate Limits & Conventions

- Rate limit: 429 on exceed — implement exponential backoff, check `Retry-After` header
- Request timeout: 60s max
- Pagination: cursor-based (`start_cursor` / `next_cursor` / `has_more`)
- IDs: UUIDv4, dashes optional in requests
- Timestamps: ISO 8601
- Empty strings: not supported — use `null`
- Max `page_size`: 100

---

## Pagination Pattern

All list endpoints return:
```json
{
  "object": "list",
  "results": [...],
  "next_cursor": "string or null",
  "has_more": true
}
```

Pass `start_cursor` to get next page. Loop until `has_more: false`.

---

## Pages

```
# Retrieve
GET /v1/pages/{page_id}
GET /v1/pages/{page_id}?filter_properties=prop1,prop2

# Create
POST /v1/pages
{
  "parent": { "type": "page_id", "page_id": "..." },        // child page
  // OR
  "parent": { "type": "database_id", "database_id": "..." }, // db row
  "properties": { "title": { "title": [{ "text": { "content": "..." } }] } },
  "children": [...]   // optional block content
}

# Update
PATCH /v1/pages/{page_id}
{
  "properties": { ... },
  "in_trash": false,
  "icon": { "type": "emoji", "emoji": "📄" },
  "cover": { "type": "external", "external": { "url": "https://..." } }
}

# Trash / restore
PATCH /v1/pages/{page_id}
{ "in_trash": true }   // or false to restore
```

**Note:** Retrieve returns properties only — not content. Use block children for content.

---

## Databases

```
# Retrieve
GET /v1/databases/{database_id}

# Create
POST /v1/databases
{
  "parent": { "type": "page_id", "page_id": "..." },
  "title": [{ "type": "text", "text": { "content": "DB Name" } }],
  "is_inline": false
}

# Update
PATCH /v1/databases/{database_id}
{
  "title": [...],
  "description": [...],
  "is_inline": true,
  "in_trash": false
}

# Query (most used)
POST /v1/databases/{database_id}/query
{
  "filter": { ... },
  "sorts": [ ... ],
  "page_size": 100,
  "start_cursor": "..."
}
```

---

## Database Filters

**Simple:**
```json
{ "property": "Status", "status": { "equals": "In Progress" } }
```

**Compound:**
```json
{
  "and": [
    { "property": "Done", "checkbox": { "equals": false } },
    {
      "or": [
        { "property": "Priority", "select": { "equals": "High" } },
        { "property": "Priority", "select": { "equals": "Critical" } }
      ]
    }
  ]
}
```

**Operators by type:**

| Type | Operators |
|---|---|
| `title` / `rich_text` / `url` / `email` | `equals`, `does_not_equal`, `contains`, `does_not_contain`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty` |
| `number` | `equals`, `does_not_equal`, `greater_than`, `less_than`, `greater_than_or_equal_to`, `less_than_or_equal_to`, `is_empty`, `is_not_empty` |
| `checkbox` | `equals` (true/false), `does_not_equal` |
| `select` | `equals`, `does_not_equal`, `is_empty`, `is_not_empty` |
| `multi_select` | `contains`, `does_not_contain`, `is_empty`, `is_not_empty` |
| `status` | `equals`, `does_not_equal`, `is_empty`, `is_not_empty` |
| `date` / `created_time` / `last_edited_time` | `after`, `before`, `on_or_after`, `on_or_before`, `equals`, `is_empty`, `is_not_empty`, `past_week`, `past_month`, `past_year`, `next_week`, `next_month`, `next_year` |
| `people` | `contains`, `does_not_contain`, `is_empty`, `is_not_empty` |
| `relation` | `contains`, `does_not_contain`, `is_empty`, `is_not_empty` |

---

## Database Sorts

```json
{
  "sorts": [
    { "property": "Priority", "direction": "descending" },
    { "timestamp": "created_time", "direction": "ascending" }
  ]
}
```

`timestamp` options: `created_time`, `last_edited_time`
`direction` options: `ascending`, `descending`

---

## Blocks

```
# Get children of a page or block
GET /v1/blocks/{block_id}/children?page_size=100&start_cursor=...

# Append children
PATCH /v1/blocks/{block_id}/children
{ "children": [ { block object }, ... ] }

# Update block content
PATCH /v1/blocks/{block_id}
{ "paragraph": { "rich_text": [{ "type": "text", "text": { "content": "..." } }] } }

# Delete block
DELETE /v1/blocks/{block_id}
```

---

## Block Types

All blocks share: `object`, `id`, `parent`, `created_time`, `last_edited_time`, `in_trash`, `has_children`

**Text blocks:**
```json
// Paragraph
{ "type": "paragraph", "paragraph": { "rich_text": [...], "color": "default" } }

// Headings (heading_1, heading_2, heading_3)
{ "type": "heading_1", "heading_1": { "rich_text": [...], "is_toggleable": false } }

// Bulleted list
{ "type": "bulleted_list_item", "bulleted_list_item": { "rich_text": [...] } }

// Numbered list
{ "type": "numbered_list_item", "numbered_list_item": { "rich_text": [...] } }

// To-do
{ "type": "to_do", "to_do": { "rich_text": [...], "checked": false } }

// Toggle
{ "type": "toggle", "toggle": { "rich_text": [...] } }

// Quote
{ "type": "quote", "quote": { "rich_text": [...] } }

// Callout
{ "type": "callout", "callout": { "rich_text": [...], "icon": { "type": "emoji", "emoji": "💡" }, "color": "blue_background" } }

// Code
{ "type": "code", "code": { "rich_text": [...], "language": "python" } }
```

**Media blocks:**
```json
// Image / Video / Audio / PDF (same shape)
{ "type": "image", "image": { "type": "external", "external": { "url": "https://..." } } }

// Bookmark
{ "type": "bookmark", "bookmark": { "url": "https://..." } }

// Embed
{ "type": "embed", "embed": { "url": "https://..." } }
```

**Structural blocks:**
```json
// Divider
{ "type": "divider", "divider": {} }

// Table of contents
{ "type": "table_of_contents", "table_of_contents": {} }

// Table
{ "type": "table", "table": { "table_width": 3, "has_column_header": true } }

// Table row (child of table)
{ "type": "table_row", "table_row": { "cells": [ [rich_text], [rich_text] ] } }
```

---

## Rich Text Object

```json
{
  "type": "text",
  "text": { "content": "Hello", "link": { "url": "https://..." } },
  "annotations": {
    "bold": false, "italic": false, "strikethrough": false,
    "underline": false, "code": false,
    "color": "default"
  }
}
```

**Annotation colors:** `default`, `gray`, `brown`, `red`, `orange`, `yellow`, `green`, `blue`, `purple`, `pink` + `_background` variants

**Mention types:** `user`, `page`, `database`, `date`

---

## Users

```
# Get user by ID
GET /v1/users/{user_id}

# List all users (paginated)
GET /v1/users?page_size=100&start_cursor=...

# Get current bot/integration
GET /v1/users/me
```

**User object:**
```json
{
  "object": "user", "id": "...",
  "type": "person",
  "name": "...", "avatar_url": "...",
  "person": { "email": "..." }
}
```

---

## Search

```
POST /v1/search
{
  "query": "search term",         // omit to get all accessible content
  "filter": { "value": "page", "property": "object" },  // or "database"
  "sort": { "direction": "descending", "timestamp": "last_edited_time" },
  "page_size": 100,
  "start_cursor": "..."
}
```

---

## Comments

```
# List comments on page or block
GET /v1/comments?block_id={page_or_block_id}&page_size=100

# Create comment on page
POST /v1/comments
{
  "parent": { "type": "page_id", "page_id": "..." },
  "rich_text": [{ "type": "text", "text": { "content": "..." } }]
}

# Create reply in thread
POST /v1/comments
{
  "discussion_id": "...",
  "rich_text": [{ "type": "text", "text": { "content": "..." } }]
}

# Update comment
PATCH /v1/comments/{comment_id}
{ "rich_text": [...] }

# Delete comment
DELETE /v1/comments/{comment_id}
```

---

## Database Property Types

24 types total:

| Type | Use |
|---|---|
| `title` | Page title (required on all pages) |
| `rich_text` | Formatted text |
| `number` | Numeric value |
| `select` | Single choice |
| `multi_select` | Multiple choices |
| `status` | Status with color groups |
| `date` | Date or date range |
| `people` | User references |
| `files` | File attachments |
| `checkbox` | Boolean |
| `url` | Web link |
| `email` | Email address |
| `phone_number` | Phone string |
| `formula` | Computed (text/number/date/boolean) |
| `relation` | Links to another DB |
| `rollup` | Aggregates from relation |
| `created_time` | Read-only creation timestamp |
| `last_edited_time` | Read-only edit timestamp |
| `created_by` | Read-only creator |
| `last_edited_by` | Read-only last editor |
| `unique_id` | Auto-incrementing ID with prefix |
| `verification` | Wiki verification status |

---

## Error Codes

| Code | Meaning |
|---|---|
| 400 | Bad request / malformed body |
| 401 | Invalid or missing token |
| 403 | Integration lacks capability |
| 404 | Not found or not shared with integration |
| 409 | Transaction conflict |
| 429 | Rate limited |
| 500 | Server error |
| 503 | Service unavailable / timeout |
| 504 | Gateway timeout (>60s) |
