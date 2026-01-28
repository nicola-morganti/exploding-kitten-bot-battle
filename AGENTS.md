# Agent Guidelines

## Project Overview

This is a Python-based bot battle card game framework. Students write bots that compete against each other.

## Key Patterns

### Type Safety
- **Always** declare types for all variables, parameters, and return values
- Use `pyright` in strict mode for type checking
- Prefer `tuple` over `list` for immutable sequences exposed to bots

### Anti-Cheat Architecture
- `GameState` is **never** exposed directly to bots
- Bots receive a `BotView` - a safe, read-only snapshot
- `BotView` only contains information the bot is allowed to see
- Callbacks that could expose the engine instance (like chat) are replaced with `queue.Queue` to break reference chains (BotView -> Queue -> Engine)

### Card System
- Each card type is a class extending `Card` base class
- Cards define their own behavior via `can_play()`, `execute()`, etc.
- Card instances are created from the `CardRegistry` based on config

### Event History
- Every game action creates a `GameEvent`
- Events are recorded in `GameHistory` for future replay
- Use `GameEvent` for both history and bot notifications

### Deterministic RNG
- All randomness goes through `DeterministicRNG`
- Same seed = same game outcome (given same bot behavior)
- Useful for testing and debugging

## Bot Implementation Gotchas

### 3-of-a-kind (Named Steal)
The 3-of-a-kind combo allows you to **name a specific card type** to steal from a target.
- If the target has the card, they MUST give it to you.
- If the target does NOT have the card, nothing happens (combo wasted).
- Use `PlayComboAction(cards=..., target_player_id=..., target_card_type="DefuseCard")` to specify the card.
- This is powerful for hunting Defuse cards when you know an opponent is hoarding them.

### 5-Different Combo (Pick from Discard)
The **5-different** combo allows you to **pick any card** currently in the discard pile.
- Use `PlayComboAction(cards=..., target_card_type="DefuseCard")` to specify the card you want.
- The engine will search the discard pile for a card of that type.
- If found, you get it. If not found (or specified), it defaults to the top card (or nothing if empty).
- **Tip**: Check `view.discard_pile` to see what's available before asking!

## File Organization

```
src/game/           # Core engine (protected)
  ├── cards/        # Card base class and registry
  └── bots/         # Bot interface and loader
bots/               # User bots (loaded at runtime)
configs/            # Deck configurations
tests/              # Test suite
```

## Testing

- Use seeded RNG for deterministic tests
- Test cards in isolation before integration
- Verify `BotView` doesn't leak protected information

## Game Setup Rules

Per official Exploding Kittens rules, `setup_game` follows this flow:
1. Remove Exploding Kittens and Defuse cards from deck
2. Validate Defuse count ≥ (players + 1) - **warns and auto-adds if needed**
3. Generate exactly **(players - 1)** Exploding Kittens at runtime
4. Deal initial hands (7 cards) from safe cards only
5. Give each player 1 Defuse card
6. Shuffle Exploding Kittens and remaining Defuse cards back into deck

**Note:** `ExplodingKittenCard` should NOT be in deck config - always auto-generated.

## Chat System

Bots can "talk" at any time using `view.say()`:

### Key Points
- Call `view.say(message)` to send a chat message in any bot method
- Works in `take_turn()`, `react()`, `on_event()`, `choose_defuse_position()`, and `choose_card_to_give()`
- Messages are truncated to 200 characters to prevent spam
- Recorded in game history as `EventType.BOT_CHAT`
- Bots see chat via `view.recent_events` in subsequent calls to `on_event`
- Game logs show `[GAME]` prefix, chat shows `[CHAT]` prefix

### Implementation Pattern
The `BotView` object has a `say()` method available in all contexts:
```python
def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
    if self._should_play_nope(triggering_event):
        view.say("Not so fast!")  # Trash talk during reactions
        return PlayCardAction(card=nope_card)
    return None

def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
    view.say("Phew, that was close!")  # React to near-death experience
    return draw_pile_size  # Put it at the bottom
```

When `view.say()` is called, the engine:
1. Logs the message with `[CHAT]` prefix
2. Records a `BOT_CHAT` event in history
3. Notifies all bots via `on_event`

## Reaction Round System (Nope Chains)

The reaction system handles Nope cards with recursive nesting:

### Key Rules
- When a card is played, a reaction round starts
- The **triggering player** (who played the card) is excluded from reacting
- Each player gets ONE chance to react per round level
- Playing a Nope starts a NEW nested reaction round
- Result: odd number of Nopes = action negated

### Critical Implementation Notes
- **ALWAYS** pass `player_id` to `_run_reaction_round(event, player_id)`
- If not passed, it defaults to `current_player_id` which may be WRONG
- This bug was fixed in engine.py for both `_play_card()` and `_play_combo()`

### Nope Chain Examples
```
Skip → Nope → Action NEGATED (1 Nope = odd)
Skip → Nope → Nope → Action PROCEEDS (2 Nopes = even, counter-nope)
Skip → Nope → Nope → Nope → Action NEGATED (3 Nopes = odd, re-negate)
```

### Test Coverage
Comprehensive tests in `tests/test_nope_chains.py` verify:
- Single Nope negation
- Counter-Nope (double Nope) un-negation
- Triple Nope re-negation
- Player exclusion from own actions
- Correct card removal and discard

## CLI Modes

### Statistics Mode (`--stats`)
Run multiple games with identical bots and deck config but different seeds to collect win rate statistics:
- Uses `GameEngine(quiet_mode=True, chat_enabled=False)` to suppress all output
- Creates fresh bot instances for each game to ensure clean state
- Tracks placement distribution (1st, 2nd, 3rd, etc.) per bot with ASCII bar charts
- Use `--iterations N` to control the number of games (default: 100)
- Use `--workers N` to control parallel execution (default: CPU count)

### Verification Run
Before running statistics, a **verification game** is played with timeout enabled:
- Tests all bots with the configured timeout (default: 5 seconds)
- Any bot that times out during verification is **disqualified**
- Disqualified bots are automatically excluded from the statistics run
- The stats output shows which bots were disqualified
- If fewer than 2 bots remain after disqualification, statistics are aborted

This prevents slow/hanging bots from blocking the entire statistics run.

### Parallel Execution
Statistics mode uses `ProcessPoolExecutor` for parallel game execution:
- Each worker process loads bots fresh from file paths (avoids pickling issues)
- Worker stdout is suppressed to avoid cluttering output
- Default workers = `os.cpu_count()` when `--stats` is enabled
- Use `--workers 1` to force sequential execution if needed
- **Note:** Timeout is disabled in worker processes to avoid thread/multiprocessing deadlocks
- **Per-game timeout:** Each game has a 10-second hard limit. Games that hang are skipped and reported at the end.
- **Action limit:** Each turn has a 1000-action limit to prevent infinite loops from bots returning invalid actions repeatedly.

### Quiet Mode / Chat Control
`GameEngine` supports two flags:
- `quiet_mode`: When `True`, suppresses ALL console output (both `[GAME]` and `[CHAT]`)
- `chat_enabled`: When `False`, suppresses only `[CHAT]` messages while keeping `[GAME]` logs

CLI usage:
- `--no-chat`: Sets `chat_enabled=False` in normal mode
- `--stats`: Automatically enables both `quiet_mode=True` and `chat_enabled=False`

## Bot Timeout System

The engine enforces time limits on bot method calls to prevent games from hanging:

### Configuration
- `GameEngine(bot_timeout=5.0)`: Sets timeout in seconds (default: 5.0)
- `GameEngine(bot_timeout=None)`: Disables timeout entirely
- CLI: `--timeout 5` or `--timeout 0` (0 = disabled)

### Timeout Behavior by Method
| Method | On Timeout |
|--------|------------|
| `take_turn()` | Bot eliminated, Exploding Kitten removed from deck |
| `react()` | Reaction skipped (no penalty, bot stays alive) |
| `choose_card_to_give()` | Random card given to requester, then bot eliminated |
| `choose_defuse_position()` | Random position chosen, game continues |
| `on_event()` | Notification skipped (no penalty) |
| `on_explode()` | Last words skipped (no additional penalty) |

### Game Balance (N-1 Rule)
The game always maintains exactly **(players - 1)** Exploding Kittens. When a bot is eliminated for timeout (or any other reason outside of normal explosion), one Exploding Kitten is removed from the deck to maintain this balance.

**Kitten Removal Priority:** The **bottom-most** Exploding Kitten (furthest from being drawn) is removed. This ensures that if there are kittens at both position 1 (top) and position 5 (bottom), position 5 is removed first.

### Event Recording
Timeout eliminations are recorded as `EventType.BOT_TIMEOUT` events with method name and timeout duration in the data.

### ⚠️ Multiprocessing Gotcha
**Timeout is DISABLED in stats mode worker processes.** The timeout system uses `threading.Thread` which can cause deadlocks when combined with `ProcessPoolExecutor` on Windows. Stats mode runs games in parallel using multiprocessing, so timeout is disabled in workers to prevent hangs.

**Lambda Closure Pitfall:** When passing lambdas to `_call_with_timeout`, always capture variables by value using default arguments:
```python
# WRONG (captures by reference - causes race conditions):
lambda: bot.on_event(event, view)

# CORRECT (captures by value):
lambda b=bot, e=event, v=view: b.on_event(e, v)
```
This is critical in loops where the lambda is executed in a thread after the loop variable has changed.

## Anti-Cheat Security Measures

The engine implements multiple layers of protection against malicious bots:

### 1. ChatProxy (Write-Only Queue Access)
Bots cannot access the raw chat queue. Instead, they receive a `ChatProxy` instance that:
- Only exposes a `send(message)` method
- Automatically enforces the correct player ID (no spoofing)
- Truncates messages to 200 characters
- Uses `__slots__` and blocks `__setattr__` to prevent attribute modification

### 2. Event Isolation (Deep Copy)
All events passed to bots are **deep copies** of the originals:
- Events in `view.recent_events` are deep copied
- Events passed to `on_event()` are deep copied
- Mutations by bots cannot affect history or other bots

### 3. Exception Handling
Bot exceptions are caught and sandboxed:
- `SystemExit` and `KeyboardInterrupt` are converted to `RuntimeError`
- Exceptions in `on_event()` are silently caught (game continues)
- Exceptions in `take_turn()` propagate but don't crash the process

### 4. Input Validation
The engine validates all bot actions independently:
- Cards must be in the player's hand (identity check)
- Target players must exist and be alive
- Reaction cards are validated via `can_play_as_reaction()`
- Actions per turn are limited to 1000 (prevents infinite loops)

### Security Test Suite
The `tests/test_anti_cheat.py` file contains 31 tests covering 15 potential cheating vectors:
1. Object graph traversal via cards
2. Queue object inspection
3. Frozen dataclass bypass
4. Playing fabricated cards
5. Target player ID manipulation
6. Invalid action types
7. Out-of-bounds defuse position
8. Combo card counting manipulation
9. Reaction card spoofing
10. Exception injection
11. Memory/resource exhaustion
12. Global state pollution
13. Card reference leaking
14. GameEvent.data mutation
15. RNG prediction

### Known Limitations
**Global State Pollution**: Bots run in the same Python process and CAN monkey-patch classes. Full isolation would require subprocess sandboxing, which is out of scope for this educational framework. The framework trusts that bots are not intentionally malicious at the Python module level.

## Groq AI Bot

The `bots/bot.py` file contains `GroqBot`, an AI-powered bot using the Groq API for strategic decisions.

### Requirements
- **API Key**: Set `GROQ_API_KEY` environment variable with a key from [console.groq.com](https://console.groq.com)
- **Dependency**: `groq>=0.12.0` is included in project dependencies

### Architecture
- Uses `llama-3.3-70b-versatile` model for decisions
- Converts game state to structured prompt for AI analysis
- AI returns JSON with action choice and reasoning
- Fallback logic when API is unavailable (similar to RandomBot)

### Timeout Considerations
API calls take ~1-3 seconds. The default bot timeout is 5 seconds. In stats mode, timeout is disabled but slow responses may still impact performance.

### Extending the Bot
When modifying the AI bot:
1. Update `SYSTEM_PROMPT` to teach new strategies
2. Modify `_build_game_state_prompt()` to include more context
3. Add new methods following the existing pattern (AI call → JSON parse → fallback)
