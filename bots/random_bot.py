"""
==============================================================================
RANDOM BOT - A Reference Implementation for Students
==============================================================================

This bot makes random decisions and serves as an educational example.
Use this as a starting point to understand how bots work, then create
your own bot with better strategy!

HOW TO CREATE YOUR OWN BOT:
1. Create a new .py file in the bots/ directory
2. Copy this file's structure
3. Implement smarter logic in each method
4. Run: python -m game.main --bot bots/your_bot.py:2

KEY CONCEPTS:
- BotView: Your "window" into the game (only shows what you're allowed to see)
- Action: What you want to do (play a card, draw, chat)
- GameEvent: Something that happened in the game
- Card: A card object with properties like card_type, name, etc.
"""

import random

# =============================================================================
# IMPORTS - These are the main classes you'll need
# =============================================================================

from game.bots.base import (
    Action,           # Base type for all actions
    Bot,              # The base class your bot must inherit from
    DrawCardAction,   # Action to draw a card (ends your turn)
    PlayCardAction,   # Action to play a single card
    PlayComboAction,  # Action to play multiple cards as a combo
)
from game.bots.view import BotView  # Your view of the game state
from game.cards.base import Card     # Card objects
from game.history import GameEvent, EventType   # Events that happen in the game


# =============================================================================
# THE BOT CLASS
# =============================================================================

class RandomBot(Bot):
    """
    A simple bot that makes random decisions.
    
    This bot is intentionally "dumb" - it just randomly picks what to do.
    Use this as a reference for HOW to implement the methods, then write
    your own bot with actual strategy!
    """
    
    def __init__(self) -> None:
        """Initialize the bot with state tracking."""
        # Some fun phrases for the bot to say during turns
        self._taunts: list[str] = [
            "I have no idea what I'm doing!",
            "Meow!",
            "Watch out, I'm unpredictable!",
            "Hmm... eeny, meeny, miny, moe...",
            "Did someone say EXPLODING KITTENS?!",
            "I'm feeling lucky today!",
            "*nervously shuffles cards*",
        ]
        
        # Phrases when playing a Nope card
        self._nope_phrases: list[str] = [
            "NOPE!",
            "Not so fast!",
            "I don't think so!",
            "Nice try!",
            "Denied!",
            "Counter that!",
        ]
        
        # Phrases when defusing an Exploding Kitten
        self._defuse_phrases: list[str] = [
            "Phew, that was close!",
            "Nice try, kitty!",
            "Not today, death!",
            "I'm still here!",
            "Ha! You thought!",
            "*defuses calmly*",
        ]
        
        # Phrases when forced to give a card (Favor)
        self._give_card_phrases: list[str] = [
            "Fine, take it...",
            "Here you go, I guess...",
            "You're welcome!",
            "Don't spend it all in one place!",
            "*reluctantly hands over card*",
        ]
        
        # Phrases when observing events
        self._reaction_phrases: dict[str, list[str]] = {
            "elimination": [
                "Goodbye!",
                "Rest in pieces!",
                "Another one bites the dust!",
                "F",
            ],
            "explosion": [
                "Uh oh!",
                "RIP?",
                "*grabs popcorn*",
            ],
            "attack": [
                "Ouch!",
                "That's rough!",
                "Glad it's not me!",
            ],
        }
        
        # Last words when exploding
        self._explosion_phrases: list[str] = [
            "NOOOOO!",
            "Tell my family I love them...",
            "This is fine.",
            "I regret nothing!",
            "*dramatic death sounds*",
            "Why me?! WHY?!",
            "Curse you, kittens!",
            "At least I tried...",
            "GG everyone!",
            "I'll be back! ...wait, no I won't.",
        ]
        
        # Phrases when playing a combo
        self._combo_phrases: list[str] = [
            "Combo time!",
            "How about THIS?!",
            "Surprise!",
            "Watch this!",
            "Behold my power!",
            "*dramatic card slam*",
        ]
    
    # =========================================================================
    # REQUIRED: The name property
    # =========================================================================
    
    @property
    def name(self) -> str:
        """
        Return the bot's name. This is displayed during the game.
        
        TIP: Make it unique so you can identify your bot in the logs!
        """
        return "RandomBot"
    
    # =========================================================================
    # HELPER: Find possible combos in hand
    # =========================================================================
    
    def _find_possible_combos(
        self, hand: tuple[Card, ...]
    ) -> list[tuple[str, tuple[Card, ...]]]:
        """
        Find all possible combos in the given hand.
        
        Inputs: hand - The bot's current hand
        Returns: List of (combo_type, cards) tuples for each valid combo
        
        Combo types:
        - "two_of_a_kind": 2 cards of same type (steal random from target)
        - "three_of_a_kind": 3 cards of same type (name + steal from target)  
        - "five_different": 5 different card types (draw from discard)
        """
        combos: list[tuple[str, tuple[Card, ...]]] = []
        
        # Filter to only cards that can combo
        combo_cards = [c for c in hand if c.can_combo()]
        
        if not combo_cards:
            return combos
        
        # Group cards by type
        by_type: dict[str, list[Card]] = {}
        for card in combo_cards:
            if card.card_type not in by_type:
                by_type[card.card_type] = []
            by_type[card.card_type].append(card)
        
        # Check for two-of-a-kind and three-of-a-kind
        for card_type, cards_of_type in by_type.items():
            if len(cards_of_type) >= 3:
                # Three of a kind takes priority (stronger effect)
                combos.append(("three_of_a_kind", tuple(cards_of_type[:3])))
            elif len(cards_of_type) >= 2:
                combos.append(("two_of_a_kind", tuple(cards_of_type[:2])))
        
        # Check for five different card types
        if len(by_type) >= 5:
            # Pick one card from each of the first 5 different types
            five_cards: list[Card] = []
            for card_type in list(by_type.keys())[:5]:
                five_cards.append(by_type[card_type][0])
            combos.append(("five_different", tuple(five_cards)))
        
        return combos
    
    # =========================================================================
    # REQUIRED: take_turn - Called when it's your turn
    # =========================================================================
    
    def take_turn(self, view: BotView) -> Action:
        """
        Decide what to do on your turn.
        
        This is the main method where your strategy lives!
        
        Args:
            view: Your view of the game. Contains:
                  - view.my_hand: Your cards (tuple of Card objects)
                  - view.my_id: Your player ID
                  - view.other_players: IDs of other players
                  - view.draw_pile_count: How many cards in draw pile
                  - view.discard_pile: Cards in discard (visible to all)
                  - view.other_player_card_counts: How many cards each opponent has
                  - view.recent_events: Recent game events (including chat!)
                  - view.say(message): Send a chat message!
        
        Returns:
            An Action object: DrawCardAction, PlayCardAction, or PlayComboAction
        
        IMPORTANT: You MUST eventually return DrawCardAction() to end your turn!
                   You can play cards before drawing, but must draw to end.
        
        CHAT FEATURE:
            - Call view.say("your message") to send a chat message
            - You can chat multiple times, but keep it reasonable!
            - Messages are recorded in history and visible to all bots
        """
        
        # =====================================================================
        # CHAT EXAMPLE: Sometimes say something during your turn
        # =====================================================================
        
        # 20% chance to chat
        if random.random() < 0.2:
            message = random.choice(self._taunts)
            view.say(message)  # Just call say() - no need to return anything!
        
        # =====================================================================
        # COMBO CHECK: 20% chance to play a combo if one is possible
        # =====================================================================
        
        possible_combos = self._find_possible_combos(view.my_hand)
        
        if possible_combos and random.random() < 0.2:
            # Pick a random combo from the available ones
            combo_type, combo_cards = random.choice(possible_combos)
            
            # 50% chance to taunt when playing a combo
            if random.random() < 0.5:
                phrase = random.choice(self._combo_phrases)
                view.say(phrase)
            
            # Two-of-a-kind and three-of-a-kind need a target player
            if combo_type in ("two_of_a_kind", "three_of_a_kind"):
                if view.other_players:
                    target = random.choice(view.other_players)
                    target_card_type = None
                    if combo_type == "three_of_a_kind":
                        # Randomly guess a card type to steal
                        all_card_types = [
                            "DefuseCard", "NopeCard", "AttackCard", "SkipCard", 
                            "SeeTheFutureCard", "ShuffleCard", "FavorCard",
                            "TacoCat", "BeardCat", "RainbowRalphingCat", "HairyPotatoCat", "Cattermelon"
                        ]
                        target_card_type = random.choice(all_card_types)
                        
                    return PlayComboAction(
                        cards=combo_cards, 
                        target_player_id=target,
                        target_card_type=target_card_type
                    )
            # Five different doesn't need a target (draws from discard)
            elif combo_type == "five_different":
                # Pick a random type that is actually in the discard pile
                # If discard is empty, we play it blindly (game will log it empty)
                target_card_type = None
                if view.discard_pile:
                    random_card = random.choice(view.discard_pile)
                    target_card_type = random_card.card_type
                
                return PlayComboAction(cards=combo_cards, target_card_type=target_card_type)
        
        # =====================================================================
        # STRATEGY: 50% chance to play a card, 50% to just draw
        # =====================================================================
        
        if random.random() < 0.5:
            # Try to find a playable card
            playable_cards = [
                card for card in view.my_hand
                if card.can_play(view, is_own_turn=True)
            ]
            
            if playable_cards:
                # Pick a random playable card
                card_to_play = random.choice(playable_cards)
                
                # If it's a Favor card, we need to specify a target
                if card_to_play.card_type == "FavorCard":
                    if view.other_players:
                        target = random.choice(view.other_players)
                        return PlayCardAction(card=card_to_play, target_player_id=target)
                
                return PlayCardAction(card=card_to_play)
        
        # Default: Draw a card to end the turn
        # This is the safe option and MUST be done eventually!
        return DrawCardAction()
    
    # =========================================================================
    # REQUIRED: on_event - Called when something happens in the game
    # =========================================================================
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """
        React to events that happen in the game.
        
        This is called for EVERY event, so you can track what's happening.
        Useful for remembering what cards opponents have played.
        
        Args:
            event: The event that just happened. Contains:
                   - event.event_type: What kind of event (CARD_PLAYED, etc.)
                   - event.player_id: Who triggered the event
                   - event.data: Extra info (card_type, target, etc.)
            view: Current game state
        
        Returns:
            None (this is for information only, you can't take actions here)
        
        EXAMPLE EVENTS:
            - EventType.CARD_PLAYED: Someone played a card
            - EventType.CARD_DRAWN: Someone drew a card
            - EventType.PLAYER_ELIMINATED: Someone exploded!
        
        NOTE: Do NOT chat in response to BOT_CHAT events to avoid infinite loops!
        """
        
        # Skip chat events to avoid infinite chat loops!
        if event.event_type == EventType.BOT_CHAT:
            return
        
        # 15% chance to comment on interesting events
        if random.random() < 0.15:
            if event.event_type == EventType.PLAYER_ELIMINATED:
                phrase = random.choice(self._reaction_phrases["elimination"])
                view.say(phrase)
            elif event.event_type == EventType.EXPLODING_KITTEN_DRAWN:
                # Only comment if it's not us
                if event.player_id != view.my_id:
                    phrase = random.choice(self._reaction_phrases["explosion"])
                    view.say(phrase)
            elif event.event_type == EventType.TURNS_ADDED:
                # Someone got attacked
                if event.player_id != view.my_id:
                    phrase = random.choice(self._reaction_phrases["attack"])
                    view.say(phrase)
    
    # =========================================================================
    # REQUIRED: react - Called when you can play a Nope card
    # =========================================================================
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        """
        Decide whether to play a reaction card (like Nope).
        
        This is called when another player does something you can react to.
        You can play a Nope card to cancel their action!
        
        Args:
            view: Current game state
            triggering_event: The event you can react to (usually CARD_PLAYED)
        
        Returns:
            PlayCardAction with a Nope card to cancel the action, or
            None to let the action happen
        
        TIP: Be strategic with Nope cards! They're valuable.
             Consider: Is this action really hurting me?
        """
        
        # Find if we have a Nope card
        nope_cards = [c for c in view.my_hand if c.card_type == "NopeCard"]
        
        if nope_cards:
            # Random bot: 30% chance to use Nope
            if random.random() < 0.3:
                # 50% chance to taunt when playing Nope
                if random.random() < 0.5:
                    phrase = random.choice(self._nope_phrases)
                    view.say(phrase)
                return PlayCardAction(card=nope_cards[0])
        
        # Don't react
        return None
    
    # =========================================================================
    # REQUIRED: choose_defuse_position - Called when you defuse a bomb
    # =========================================================================
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        Choose where to put the Exploding Kitten back in the deck.
        
        This is called after you successfully defuse an Exploding Kitten.
        You get to secretly put it back anywhere in the draw pile!
        
        Args:
            view: Current game state
            draw_pile_size: How many cards are in the draw pile
        
        Returns:
            An integer position:
            - 0 = top of the pile (next player gets it!)
            - draw_pile_size = bottom of the pile (safest for you)
            - Anywhere in between
        
        STRATEGY TIP: Put it where your opponent will draw it!
        """
        
        # 40% chance to say something when defusing
        if random.random() < 0.4:
            phrase = random.choice(self._defuse_phrases)
            view.say(phrase)
        
        # Random position from top to bottom
        return random.randint(0, draw_pile_size)
    
    # =========================================================================
    # REQUIRED: choose_card_to_give - Called when hit by Favor
    # =========================================================================
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """
        Choose which card to give when someone plays Favor on you.
        
        You MUST give them a card - you choose which one.
        
        Args:
            view: Current game state (view.my_hand has your cards)
            requester_id: The player who's asking for a card
        
        Returns:
            A Card from your hand to give away
        
        STRATEGY TIP: Give away your least valuable cards!
                      Keep Defuse and Nope cards if possible.
        """
        
        hand = list(view.my_hand)
        
        # 30% chance to comment when giving a card
        if random.random() < 0.3:
            phrase = random.choice(self._give_card_phrases)
            view.say(phrase)
        
        # Priority: Keep valuable cards, give away junk
        # 1. Try to give a cat card (useless alone)
        cat_cards = [c for c in hand if "Cat" in c.card_type]
        if cat_cards:
            return random.choice(cat_cards)
        
        # 2. Give anything that's NOT Defuse or Nope
        safe_to_give = [c for c in hand if c.card_type not in ("DefuseCard", "NopeCard")]
        if safe_to_give:
            return random.choice(safe_to_give)
        
        # 3. Last resort: give something (can't keep it)
        return random.choice(hand)
    
    # =========================================================================
    # REQUIRED: on_explode - Called when you're about to die
    # =========================================================================
    
    def on_explode(self, view: BotView) -> None:
        """
        Say your last words before being eliminated.
        
        This is called when you draw an Exploding Kitten with no Defuse.
        You're about to explode - this is your final chance to chat!
        
        Args:
            view: Current game state
        
        TIP: Use view.say() to leave a memorable last message!
        """
        
        # Always say something dramatic when exploding!
        phrase = random.choice(self._explosion_phrases)
        view.say(phrase)
