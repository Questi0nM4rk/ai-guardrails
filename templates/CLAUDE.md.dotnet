# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Describe your .NET project here]

## Stack

- .NET 8/9/10
- C# 12/13
- [Add your frameworks: ASP.NET Core, EF Core, etc.]

## Commands

```bash
# Build
dotnet build --warnaserror

# Test
dotnet test --verbosity normal

# Test single
dotnet test --filter "FullyQualifiedName~ClassName.MethodName"

# Run
dotnet run --project src/YourProject

# Format
dotnet format

# Watch
dotnet watch --project src/YourProject
```

## Architecture

[Describe your architecture - layers, patterns used]

Example:

```text
src/
├── Domain/          # Entities, value objects, domain logic
├── Application/     # Use cases, DTOs, interfaces
├── Infrastructure/  # External concerns (DB, APIs)
└── Api/             # HTTP endpoints, controllers
```

## Conventions

- Primary constructors for dependency injection
- `Result<T>` for error handling (no exceptions for flow control)
- Nullable reference types enabled
- XML docs on public APIs
- Tests mirror src/ structure in tests/

## Patterns in Use

[List patterns your project uses]

- CQRS with MediatR
- Repository pattern
- Unit of Work
- Domain Events

## Database

[Your database setup]

```bash
# Migrations
dotnet ef migrations add MigrationName

# Update
dotnet ef database update
```

## Testing

```bash
# All tests
dotnet test

# With coverage
dotnet test --collect:"XPlat Code Coverage"

# Specific test
dotnet test --filter "ClassName.TestMethod"
```
