"""
Abstract base class for all bots.

Bots implement this interface to participate in the game. The interface
provides methods for taking turns, reacting to events, and responding
during reaction rounds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.bots.view import BotView
    from game.cards.base import Card
    from game.history import GameEvent


@dataclass(frozen=True)
class PlayCardAction:
    """Action to play a single card."""
    
    card: Card
    target_player_id: str | None = None  # For cards that target a player


@dataclass(frozen=True)
class PlayComboAction:
    """Action to play a combo of cards."""
    
    cards: tuple[Card, ...]
    target_player_id: str | None = None
    target_card_type: str | None = None  # For 3-of-a-kind (naming a card) OR 5-different (picking from discard)


@dataclass(frozen=True)
class DrawCardAction:
    """Action to draw a card (end turn normally)."""
    
    pass



@dataclass(frozen=True)
class DefuseAction:
    """
    Action to defuse an Exploding Kitten.
    
    Attributes:
        insert_position: Where to insert the kitten in the draw pile.
                        0 = top (next to draw), len(draw_pile) = bottom.
    """
    
    insert_position: int


@dataclass(frozen=True)
class GiveCardAction:
    """
    Action to give a card to another player (response to Favor).
    
    Attributes:
        card: The card to give.
    """
    
    card: Card


# Type alias for all possible actions
Action = (
    PlayCardAction
    | PlayComboAction
    | DrawCardAction
    | DefuseAction
    | GiveCardAction
)


class Bot(ABC):
    """
    Abstract base class for all bots.
    
    Bot implementations must provide:
    - A name for identification
    - Logic for taking turns
    - Logic for observing events
    - Logic for reacting during reaction rounds
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        The display name of this bot.
        
        Returns:
            A human-readable name for the bot.
        """
        ...
    
    @abstractmethod
    def take_turn(self, view: BotView) -> Action:
        """
        Called when it's this bot's turn to play.
        
        The bot should decide what action to take based on the current
        game state (visible through the view).
        
        Args:
            view: The bot's view of the game state.
            
        Returns:
            The action to take. Return DrawCardAction to end the turn
            by drawing a card.
        """
        ...
    
    @abstractmethod
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """
        Called when any game event occurs.
        
        This is for information only - the bot cannot take action here.
        Use this to track game state and other players' actions.
        
        Args:
            event: The event that occurred.
            view: The bot's current view of the game state.
        """
        ...
    
    @abstractmethod
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        """
        Called during a reaction round to allow playing reaction cards.
        
        This is called after another player plays a card, giving this bot
        a chance to play a reaction card (like Nope) if it has one.
        
        Args:
            view: The bot's view of the game state.
            triggering_event: The event that triggered this reaction round.
            
        Returns:
            An action to take (typically PlayCardAction with a reaction card),
            or None to decline reacting.
        """
        ...
    
    @abstractmethod
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        Choose where to reinsert the Exploding Kitten after defusing.
        
        Called when the bot successfully defuses an Exploding Kitten.
        The position is secret - other bots won't know where it was placed.
        
        Args:
            view: The bot's view of the game state.
            draw_pile_size: Current size of the draw pile (for bounds).
            
        Returns:
            Position to insert (0 = top/next to draw, draw_pile_size = bottom).
        """
        ...
    
    @abstractmethod
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """
        Choose a card to give to another player (Favor card response).
        
        Called when another player plays a Favor card targeting this bot.
        
        Args:
            view: The bot's view of the game state.
            requester_id: The player who played the Favor card.
            
        Returns:
            A card from the bot's hand to give away.
        """
        ...
    
    @abstractmethod
    def on_explode(self, view: BotView) -> None:
        """
        Called when this bot is about to explode (no Defuse card).
        
        This is the bot's last chance to say something before being eliminated.
        Use view.say() to send a final message!
        
        Args:
            view: The bot's view of the game state.
        """
        ...
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(name={self.name!r})"

