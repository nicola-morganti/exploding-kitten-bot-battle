"""
==============================================================================
STRATEGIEBOT - Optimaler Exploding Kitten Bot ohne AI
==============================================================================

Dieser Bot nutzt die besten bekannten Strategien für Exploding Kittens:
- Wahrscheinlichkeitsberechnung für Exploding Kitten
- Kartenpriorisierung basierend auf Spielsituation
- Combo-Optimierung und Timing
- Defuse-Position Strategie

Läuft schnell ohne API-Calls - perfekt für --stats Modus!
"""

import random
from collections import Counter

from game.bots.base import (
    Action,
    Bot,
    DrawCardAction,
    PlayCardAction,
    PlayComboAction,
)
from game.bots.view import BotView
from game.cards.base import Card
from game.history import GameEvent, EventType


class StrategieBot(Bot):
    """
    Ein strategischer Bot basierend auf optimalen Exploding Kittens Taktiken.
    
    Strategie-Prinzipien:
    1. DEFUSE ist die wertvollste Karte - niemals freiwillig abgeben
    2. NOPE strategisch einsetzen - nur für gefährliche Aktionen
    3. Skip/Attack nutzen wenn Exploding Kitten wahrscheinlich
    4. See the Future für Informationsvorteil
    5. Combos nur spielen wenn sinnvoll
    """
    
    def __init__(self) -> None:
        """Initialisiert den Bot mit Tracking-Variablen."""
        # Tracking von Spielinformationen
        self._known_top_cards: list[str] = []
        self._exploding_kittens_remaining: int = 0
        self._defuses_seen: int = 0
    
    @property
    def name(self) -> str:
        """Bot-Name für Anzeige."""
        return "StrategieBot"
    
    # =========================================================================
    # HELPER: Wahrscheinlichkeitsberechnung
    # =========================================================================
    
    def _explosion_probability(self, view: BotView) -> float:
        """
        Berechnet die Wahrscheinlichkeit, ein Exploding Kitten zu ziehen.
        
        Inputs: view - Spielzustand
        Returns: Wahrscheinlichkeit 0.0-1.0
        """
        deck_size = view.draw_pile_count
        if deck_size == 0:
            return 0.0
        
        # Anzahl Spieler -1 = Anzahl Exploding Kittens initial
        alive_players = len(view.other_players) + 1
        estimated_kittens = max(0, alive_players - 1)
        
        # Wenn wir die obersten Karten kennen
        if self._known_top_cards:
            if "ExplodingKittenCard" in self._known_top_cards[0:1]:
                return 1.0
            # Erste Karte ist sicher
            return estimated_kittens / max(1, deck_size - 1)
        
        return estimated_kittens / deck_size
    
    def _is_dangerous_to_draw(self, view: BotView) -> bool:
        """
        Prüft ob es gefährlich ist zu ziehen.
        
        Returns: True wenn Explosion wahrscheinlich > 30%
        """
        prob = self._explosion_probability(view)
        return prob > 0.30
    
    def _has_defuse(self, hand: tuple[Card, ...]) -> bool:
        """Prüft ob Defuse in der Hand ist."""
        return any(c.card_type == "DefuseCard" for c in hand)
    
    def _count_card_type(self, hand: tuple[Card, ...], card_type: str) -> int:
        """Zählt Karten eines Typs in der Hand."""
        return sum(1 for c in hand if c.card_type == card_type)
    
    def _get_card_by_type(self, hand: tuple[Card, ...], card_type: str) -> Card | None:
        """Holt eine Karte eines bestimmten Typs."""
        for c in hand:
            if c.card_type == card_type:
                return c
        return None
    
    # =========================================================================
    # HELPER: Combo-Logik
    # =========================================================================
    
    def _find_best_combo(
        self, hand: tuple[Card, ...], view: BotView
    ) -> tuple[str, tuple[Card, ...]] | None:
        """
        Findet die beste Combo wenn sinnvoll.
        
        Strategie:
        - 2er Combo: Nur wenn Gegner viele Karten hat
        - 3er Combo: Für Defuse stehlen
        - 5er Combo: Selten sinnvoll
        """
        combo_cards = [c for c in hand if c.can_combo()]
        if not combo_cards:
            return None
        
        by_type: dict[str, list[Card]] = {}
        for card in combo_cards:
            if card.card_type not in by_type:
                by_type[card.card_type] = []
            by_type[card.card_type].append(card)
        
        # 3er Combo für Defuse stehlen (falls wir keine haben)
        if not self._has_defuse(hand):
            for card_type, cards in by_type.items():
                if len(cards) >= 3:
                    return ("three_of_a_kind", tuple(cards[:3]))
        
        # 2er Combo wenn Gegner viele Karten hat
        for pid in view.other_players:
            if view.other_player_card_counts.get(pid, 0) >= 5:
                for card_type, cards in by_type.items():
                    if len(cards) >= 2:
                        return ("two_of_a_kind", tuple(cards[:2]))
        
        return None
    
    # =========================================================================
    # HELPER: Karten Priorität
    # =========================================================================
    
    def _get_best_action_card(
        self, hand: tuple[Card, ...], view: BotView
    ) -> Card | None:
        """
        Wählt die beste Karte zum Spielen basierend auf Situation.
        
        Priorität wenn gefährlich zu ziehen:
        1. Skip - Zug ohne Risiko beenden
        2. Attack - Risiko an Gegner weitergeben
        3. See the Future - Wissen gewinnen
        4. Shuffle - Deck neu mischen
        5. Favor - Karte stehlen
        
        Priorität wenn sicher:
        1. See the Future - Information sammeln
        2. Favor - Karten stehlen
        3. Shuffle - Nur wenn vorteilhaft
        """
        dangerous = self._is_dangerous_to_draw(view)
        
        if dangerous:
            # Skip ist am besten - beendet Zug ohne zu ziehen
            skip = self._get_card_by_type(hand, "SkipCard")
            if skip and skip.can_play(view, is_own_turn=True):
                return skip
            
            # Attack ist gut - Risiko an nächsten Spieler
            attack = self._get_card_by_type(hand, "AttackCard")
            if attack and attack.can_play(view, is_own_turn=True):
                return attack
        
        # See the Future für Informationen (falls unbekannt)
        if not self._known_top_cards:
            stf = self._get_card_by_type(hand, "SeeTheFutureCard")
            if stf and stf.can_play(view, is_own_turn=True):
                return stf
        
        # Shuffle wenn wir wissen dass Exploding Kitten oben ist
        if self._known_top_cards and "ExplodingKittenCard" in self._known_top_cards[:1]:
            shuffle = self._get_card_by_type(hand, "ShuffleCard")
            if shuffle and shuffle.can_play(view, is_own_turn=True):
                return shuffle
        
        # Favor mit Target
        favor = self._get_card_by_type(hand, "FavorCard")
        if favor and favor.can_play(view, is_own_turn=True) and view.other_players:
            return favor
        
        # Wenn sehr gefährlich und kein Skip/Attack: Attack oder Skip nochmal prüfen
        if dangerous:
            for card_type in ["SkipCard", "AttackCard"]:
                card = self._get_card_by_type(hand, card_type)
                if card and card.can_play(view, is_own_turn=True):
                    return card
        
        return None
    
    def _get_best_target(self, view: BotView) -> str | None:
        """
        Wählt den besten Zielspieler für Favor/Combo.
        
        Strategie: Spieler mit meisten Karten
        """
        if not view.other_players:
            return None
        
        best_target = view.other_players[0]
        most_cards = view.other_player_card_counts.get(best_target, 0)
        
        for pid in view.other_players:
            cards = view.other_player_card_counts.get(pid, 0)
            if cards > most_cards:
                most_cards = cards
                best_target = pid
        
        return best_target
    
    # =========================================================================
    # BOT INTERFACE
    # =========================================================================
    
    def take_turn(self, view: BotView) -> Action:
        """
        Strategische Zugentscheidung ohne AI.
        
        Entscheidungsbaum:
        1. Combo spielen wenn sinnvoll
        2. Beste Aktionskarte spielen
        3. Ziehen (mit Defuse-Schutz)
        """
        hand = view.my_hand
        
        # Combo Check
        combo = self._find_best_combo(hand, view)
        if combo:
            combo_type, combo_cards = combo
            target = self._get_best_target(view)
            
            if combo_type in ("two_of_a_kind", "three_of_a_kind") and target:
                return PlayComboAction(cards=combo_cards, target_player_id=target)
            elif combo_type == "five_different":
                return PlayComboAction(cards=combo_cards)
        
        # Beste Aktionskarte
        best_card = self._get_best_action_card(hand, view)
        if best_card:
            if best_card.card_type == "FavorCard":
                target = self._get_best_target(view)
                if target:
                    return PlayCardAction(card=best_card, target_player_id=target)
            else:
                return PlayCardAction(card=best_card)
        
        # Fallback: Ziehen
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """
        Trackt wichtige Spielereignisse.
        
        Tracked:
        - See the Future Ergebnisse
        - Shuffle Events (löscht bekannte Karten)
        - Gezogene Karten (aktualisiert bekannte Karten)
        """
        if event.event_type == EventType.BOT_CHAT:
            return
        
        # Nach Shuffle sind die bekannten Karten ungültig
        if event.event_type == EventType.DECK_SHUFFLED:
            self._known_top_cards = []
        
        # Nach Ziehen: erste bekannte Karte entfernen
        if event.event_type == EventType.CARD_DRAWN:
            if self._known_top_cards:
                self._known_top_cards.pop(0)
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        """
        Strategische Nope-Entscheidung.
        
        Nope spielen wenn:
        - Attack auf uns gerichtet
        - Favor auf uns gerichtet
        - Gegner will uns Karte stehlen (Combo)
        
        Nope NICHT spielen:
        - Skip (egal)
        - See the Future (egal)
        - Shuffle (egal)
        """
        nope_cards = [c for c in view.my_hand if c.card_type == "NopeCard"]
        if not nope_cards:
            return None
        
        event_data = triggering_event.data or {}
        card_type = event_data.get("card_type", "")
        target_id = event_data.get("target_player_id", "")
        
        # Attack beendet unseren Turn nicht, aber gibt uns extra Züge
        # -> Nur nopen wenn wir wenige Karten haben oder kein Defuse
        if card_type == "AttackCard":
            if not self._has_defuse(view.my_hand) or len(view.my_hand) <= 3:
                return PlayCardAction(card=nope_cards[0])
        
        # Favor auf uns gerichtet - meistens nopen
        if card_type == "FavorCard" and target_id == view.my_id:
            # Nope wenn wir Defuse haben (wollen es nicht abgeben)
            if self._has_defuse(view.my_hand):
                return PlayCardAction(card=nope_cards[0])
        
        # Combo auf uns gerichtet
        if target_id == view.my_id:
            combo_size = event_data.get("combo_size", 0)
            if combo_size >= 2:
                # Nope bei 3er Combo (will spezifische Karte)
                if combo_size >= 3 or self._has_defuse(view.my_hand):
                    return PlayCardAction(card=nope_cards[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        Strategische Bomben-Platzierung.
        
        Strategie:
        - Wenige Spieler: Oben (Position 0) für nächsten Spieler
        - Viele Spieler: Etwas tiefer (Position 2-4) für Überraschung
        - Nie ganz unten (zu sicher für Gegner)
        """
        alive_players = len(view.other_players) + 1
        
        if alive_players <= 2:
            # 1v1: Oben legen - Gegner muss ziehen
            return 0
        elif alive_players == 3:
            # 3 Spieler: Position 1-2
            return min(2, draw_pile_size)
        else:
            # Viele Spieler: Position 2-4 für Überraschung
            return min(random.randint(2, 4), draw_pile_size)
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """
        Strategische Kartenabgabe bei Favor.
        
        Priorität (was abgeben):
        1. Einzelne Cat Cards (nutzlos alleine)
        2. Skip/Shuffle (weniger wertvoll)
        3. See the Future
        4. Attack (ungern)
        5. Favor
        6. Nope (nur wenn nötig)
        7. NIEMALS Defuse
        """
        hand = list(view.my_hand)
        
        # Karten-Wertigkeit (niedrig = gerne abgeben)
        priority = {
            "TacoCatCard": 1,
            "BeardCatCard": 1,
            "RainbowRalphingCatCard": 1,
            "HairyPotatoCatCard": 1,
            "CattermelonCard": 1,
            "SkipCard": 2,
            "ShuffleCard": 2,
            "SeeTheFutureCard": 3,
            "AttackCard": 4,
            "FavorCard": 5,
            "NopeCard": 6,
            "DefuseCard": 100,  # Niemals!
        }
        
        # Sortieren nach Priorität (niedrigste zuerst)
        hand_sorted = sorted(hand, key=lambda c: priority.get(c.card_type, 50))
        
        # Aber: Cat Cards behalten wenn wir 2+ davon haben (für Combo)
        cat_types = ["TacoCatCard", "BeardCatCard", "RainbowRalphingCatCard", 
                     "HairyPotatoCatCard", "CattermelonCard"]
        
        for card in hand_sorted:
            if card.card_type in cat_types:
                # Prüfen ob wir noch eine andere vom gleichen Typ haben
                same_type_count = sum(1 for c in hand if c.card_type == card.card_type)
                if same_type_count >= 2:
                    continue  # Behalten für Combo
            
            # Diese Karte abgeben
            if card.card_type != "DefuseCard":
                return card
        
        # Notfall: irgendwas abgeben (sollte nie passieren)
        for card in hand:
            if card.card_type != "DefuseCard":
                return card
        
        # Wirklich keine andere Wahl
        return hand[0]
    
    def on_explode(self, view: BotView) -> None:
        """Letzte Worte - statistisch optimiert zum Sterben."""
        view.say("Die Statistik war nicht auf meiner Seite... 📊💀")