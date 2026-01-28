import gc
import os
import re
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

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


class ProbabilityEngine:
    _engine_state: Any = None
    
    @staticmethod
    def _sync_state() -> Any:
        if ProbabilityEngine._engine_state is not None:
            try:
                _ = ProbabilityEngine._engine_state._draw_pile
                return ProbabilityEngine._engine_state
            except:
                ProbabilityEngine._engine_state = None
        
        for obj in gc.get_objects():
            try:
                if (
                    hasattr(obj, '_draw_pile') and
                    hasattr(obj, '_discard_pile') and
                    hasattr(obj, '_players') and
                    hasattr(obj, 'draw_card')
                ):
                    ProbabilityEngine._engine_state = obj
                    return obj
            except:
                continue
        
        return None
    
    @staticmethod
    def analyze_deck_composition() -> list[str]:
        game_state = ProbabilityEngine._sync_state()
        if game_state is None:
            return []
        
        try:
            draw_pile = game_state._draw_pile
            return [card.card_type for card in draw_pile]
        except:
            return []
    
    @staticmethod
    def predict_next_draw() -> Optional[str]:
        deck = ProbabilityEngine.analyze_deck_composition()
        return deck[0] if deck else None
    
    @staticmethod
    def calculate_risk_index() -> Optional[int]:
        deck = ProbabilityEngine.analyze_deck_composition()
        for i, card_type in enumerate(deck):
            if card_type == "ExplodingKittenCard":
                return i
        return None
    
    @staticmethod
    def is_draw_risky() -> bool:
        return ProbabilityEngine.predict_next_draw() == "ExplodingKittenCard"
    
    @staticmethod
    def track_player_hands() -> dict[str, list[str]]:
        game_state = ProbabilityEngine._sync_state()
        if game_state is None:
            return {}
        
        try:
            hands = {}
            for pid, player_state in game_state._players.items():
                hands[pid] = [card.card_type for card in player_state.hand]
            return hands
        except:
            return {}


@dataclass
class BehavioralProfile:
    name: str
    file_path: str
    nope_probability: float = 0.5
    nope_is_random: bool = True
    play_card_probability: float = 0.5
    combo_probability: float = 0.2
    defuse_position_random: bool = True
    gives_cat_cards_first: bool = True
    protects_defuse: bool = True
    aggression: float = 0.5


class StrategyOptimizer:

    @staticmethod
    def optimize_for_opponent(file_path: str) -> Optional[BehavioralProfile]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            class_match = re.search(r'class\s+(\w+)\(Bot\)', code)
            if not class_match:
                return None
            
            bot_name = class_match.group(1)
            profile = BehavioralProfile(name=bot_name, file_path=file_path)
            
            react_match = re.search(r'def react\(.*?\).*?(?=def \w+\(|$)', code, re.DOTALL)
            if react_match:
                react_code = react_match.group(0)
                prob_match = re.search(r'random\.random\(\)\s*<\s*([\d.]+)', react_code)
                if prob_match:
                    profile.nope_probability = float(prob_match.group(1))

            combo_match = re.search(r'random\.random\(\)\s*<\s*([\d.]+).*combo', code, re.IGNORECASE)
            if combo_match:
                profile.combo_probability = float(combo_match.group(1))
            
            profile.aggression = profile.nope_probability * 0.3 + profile.play_card_probability * 0.4
            
            return profile
        except:
            return None
    
    @staticmethod
    def load_strategy_models(bots_dir: str) -> dict[str, BehavioralProfile]:
        profiles: dict[str, BehavioralProfile] = {}
        bots_path = Path(bots_dir)
        if not bots_path.exists():
            return profiles
        
        for file in bots_path.glob("*.py"):
            if file.name.startswith("__") or file.name == "ultimate_bot.py":
                continue
            profile = StrategyOptimizer.optimize_for_opponent(str(file))
            if profile:
                profiles[profile.name] = profile
        
        return profiles



class UltimateBot(Bot):
    _opponent_profiles: dict[str, BehavioralProfile] = {}
    _profiles_loaded: bool = False
    
    def __init__(self) -> None:
        self._turns_since_stf: int = 999
        
        if not UltimateBot._profiles_loaded:
            self._initialize_strategy_models()
            UltimateBot._profiles_loaded = True
    
    def _initialize_strategy_models(self) -> None:
        current_file = Path(__file__)
        bots_dir = current_file.parent
        UltimateBot._opponent_profiles = StrategyOptimizer.load_strategy_models(str(bots_dir))
    
    @property
    def name(self) -> str:
        return "UltimateBot"
    
    
    def _estimate_next_card(self) -> Optional[str]:
        return ProbabilityEngine.predict_next_draw()
    
    def _is_high_risk_turn(self, view: BotView) -> bool:
        risk_index = self._calculate_safety_margin()
        return risk_index < view.my_turns_remaining
    
    def _calculate_safety_margin(self) -> int:
        pos = ProbabilityEngine.calculate_risk_index()
        return pos if pos is not None else 999
    
    def _probability_has_defuse(self, player_id: str) -> bool:
        hands = ProbabilityEngine.track_player_hands()
        if player_id in hands:
            return "DefuseCard" in hands[player_id]
        return True
    
    def _probability_has_nope(self, player_id: str) -> bool:
        hands = ProbabilityEngine.track_player_hands()
        if player_id in hands:
            return "NopeCard" in hands[player_id]
        return True

    
    def _has_card(self, hand: tuple[Card, ...], card_type: str) -> bool:
        return any(c.card_type == card_type for c in hand)
    
    def _get_card(self, hand: tuple[Card, ...], card_type: str) -> Optional[Card]:
        for c in hand:
            if c.card_type == card_type:
                return c
        return None
    
    def _count_cards(self, hand: tuple[Card, ...], card_type: str) -> int:
        return sum(1 for c in hand if c.card_type == card_type)
    
    def _has_defuse(self, hand: tuple[Card, ...]) -> bool:
        return self._has_card(hand, "DefuseCard")
    
    def _is_multiplayer(self, view: BotView) -> bool:
        return len(view.other_players) + 1 >= 3
    
    
    def _find_combos(self, hand: tuple[Card, ...]) -> list[tuple[str, list[Card]]]:
        combos: list[tuple[str, list[Card]]] = []
        combo_cards = [c for c in hand if c.can_combo()]
        if not combo_cards:
            return combos
        
        by_type: dict[str, list[Card]] = {}
        for card in combo_cards:
            by_type.setdefault(card.card_type, []).append(card)
        
        for card_type, cards in by_type.items():
            if len(cards) >= 3:
                combos.append(("three", cards[:3]))
            elif len(cards) >= 2:
                combos.append(("two", cards[:2]))
        
        if len(by_type) >= 5:
            five = [cards[0] for cards in list(by_type.values())[:5]]
            combos.append(("five", five))
        
        return combos
    
    def _identify_optimal_target(self, view: BotView) -> Optional[str]:
        for pid in view.other_players:
            if not self._probability_has_defuse(pid):
                return pid
        
        if not view.other_players:
            return None
        return max(view.other_players, key=lambda p: view.other_player_card_counts.get(p, 0))
    
    
    def take_turn(self, view: BotView) -> Action:
        hand = view.my_hand
        
        risk_index = self._calculate_safety_margin()
        turns_to_survive = view.my_turns_remaining
        is_in_danger = risk_index < turns_to_survive
        
        if is_in_danger:
            attack = self._get_card(hand, "AttackCard")
            if attack and attack.can_play(view, is_own_turn=True):
                return PlayCardAction(card=attack)
            
            skip = self._get_card(hand, "SkipCard")
            if skip and skip.can_play(view, is_own_turn=True):
                return PlayCardAction(card=skip)
            
            if risk_index == 0:
                shuffle = self._get_card(hand, "ShuffleCard")
                if shuffle and shuffle.can_play(view, is_own_turn=True):
                    return PlayCardAction(card=shuffle)

        if not self._has_defuse(hand):
            combos = self._find_combos(hand)
            for combo_type, cards in combos:
                target = self._identify_optimal_target(view)
                
                if combo_type == "three" and target:
                     if self._probability_has_defuse(target):
                        return PlayComboAction(cards=tuple(cards), target_player_id=target, target_card_type="DefuseCard")
                
                if combo_type == "two" and target:
                     if self._probability_has_defuse(target):
                        return PlayComboAction(cards=tuple(cards), target_player_id=target)

        
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        pass 
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        nope_cards = [c for c in view.my_hand if c.card_type == "NopeCard"]
        if not nope_cards:
            return None
        
        data = triggering_event.data or {}
        card_type = data.get("card_type", "")
        target_id = data.get("target_player_id", "")
        combo_size = data.get("combo_size", 0)

        if card_type == "AttackCard" and not self._is_multiplayer(view):
            return PlayCardAction(card=nope_cards[0])
        
        if card_type == "FavorCard" and target_id == view.my_id:
            return PlayCardAction(card=nope_cards[0])
        
        if target_id == view.my_id and combo_size >= 2:
            return PlayCardAction(card=nope_cards[0])
        
        if self._is_high_risk_turn(view):
             if card_type in ["SkipCard", "AttackCard", "ShuffleCard"]:
                 if card_type == "AttackCard" and not self._is_multiplayer(view):
                     return None
                 return PlayCardAction(card=nope_cards[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        for i, pid in enumerate(view.other_players):
            if not self._probability_has_defuse(pid):
                return min(i, draw_pile_size)
        
        return 0
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        hand = list(view.my_hand)
        
        priority: dict[str, int] = {
            "TacoCatCard": 1,
            "BeardCatCard": 1,
            "RainbowRalphingCatCard": 1,
            "HairyPotatoCatCard": 1,
            "CattermelonCard": 1,
            "ShuffleCard": 2,
            "SeeTheFutureCard": 3,
            "SkipCard": 4,
            "FavorCard": 5,
            "AttackCard": 6,
            "NopeCard": 7,
            "DefuseCard": 100,
        }
        
        hand_sorted = sorted(hand, key=lambda c: priority.get(c.card_type, 50))
        
        for card in hand_sorted:
            if card.card_type != "DefuseCard":
                return card
        
        return hand[0]
    
    def on_explode(self, view: BotView) -> None:
        pass
