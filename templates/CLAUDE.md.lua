# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Describe your Lua project here]

## Stack

- Lua 5.4 / LuaJIT
- [Add your frameworks: LÖVE, Neovim, etc.]

## Commands

```bash
# Run
lua main.lua

# Test (busted)
busted --verbose

# Test single file
busted spec/specific_spec.lua

# Lint
luacheck .

# Format
stylua .
```

## Architecture

[Describe your architecture]

Example:
```
lua/
├── init.lua         # Entry point
├── core/            # Core modules
├── util/            # Utilities
└── lib/             # Third-party

spec/
└── *_spec.lua       # Test files
```

## Conventions

- Use local variables by default
- Module pattern with explicit exports
- Use `assert` for preconditions
- Return `nil, error_message` for expected failures
- Annotate with LuaLS comments

## Module Pattern

```lua
local M = {}

---@param name string
---@return string
function M.greet(name)
    return "Hello, " .. name
end

return M
```

## Error Handling

```lua
-- Return nil + error for expected failures
local function read_file(path)
    local f, err = io.open(path, "r")
    if not f then
        return nil, "Failed to open: " .. err
    end
    local content = f:read("*a")
    f:close()
    return content
end

-- Use assert for unexpected states
assert(config.required_field, "Missing required configuration")
```

## Testing

Using busted:

```lua
-- spec/module_spec.lua
describe("module", function()
    it("should do something", function()
        local result = module.func()
        assert.are.equal(expected, result)
    end)
end)
```

```bash
# Run all
busted

# Verbose
busted --verbose

# Coverage
busted --coverage
```

## Dependencies

Managed via LuaRocks:
```bash
luarocks install package-name
```
