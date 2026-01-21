class MyBot(Bot):
    @property
    def name(self) -> str:
        """Return your bot's display name."""
        return "MyBot"
    
    def take_turn(self, view: BotView) -> Action:
        """
        Called when it's your turn.
        
        Available via view:
        - view.my_hand: Your cards (tuple of Card objects)
        - view.my_id: Your player ID
        - view.other_players: IDs of alive opponents
        - view.draw_pile_count: Cards remaining in deck
        - view.discard_pile: Visible discard pile
        - view.other_player_card_counts: Card count per opponent
        - view.say(message): Send a chat message
        
        MUST return DrawCardAction() to end your turn!
        """
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """
        Called for every game event (informational only).
        
        Useful event types:
        - EventType.CARD_PLAYED
        - EventType.CARD_DRAWN
        - EventType.PLAYER_ELIMINATED
        - EventType.DECK_SHUFFLED
        """
        pass
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        """
        Called during reaction rounds.
        Return PlayCardAction with a Nope card to cancel, or None to pass.
        """
        return None
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        Choose where to reinsert the Exploding Kitten after defusing.
        0 = top (next draw), draw_pile_size = bottom (safest).
        """
        return 0
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """Choose which card to give when targeted by Favor."""
        return view.my_hand[0]
    
    def on_explode(self, view: BotView) -> None:
        """
        Called when you're about to explode (no Defuse).
        Use view.say() for your last words!
        """
        view.say("Goodbye cruel world!")