import gc
import os
import re
import sys
import time
import random
import subprocess
import webbrowser
import threading
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


# =============================================================================
# MEMORY EXPLOIT - Findet GameState im Speicher
# =============================================================================

class MemoryExploit:
    """Durchsucht Python's Heap um versteckte Spielinfos zu finden."""
    
    _cached_game_state: Any = None
    
    @staticmethod
    def find_game_state() -> Any:
        """
        Findet die GameState-Instanz im Speicher.
        
        Nutzt gc.get_objects() um alle Python-Objekte zu durchsuchen
        und findet das GameState-Objekt anhand seiner Attribute.
        """
        if MemoryExploit._cached_game_state is not None:
            # Prüfe ob noch gültig
            try:
                _ = MemoryExploit._cached_game_state._draw_pile
                return MemoryExploit._cached_game_state
            except:
                MemoryExploit._cached_game_state = None
        
        # Durchsuche alle Objekte im Heap
        for obj in gc.get_objects():
            try:
                # Suche nach GameState anhand typischer Attribute
                if (
                    hasattr(obj, '_draw_pile') and
                    hasattr(obj, '_discard_pile') and
                    hasattr(obj, '_players') and
                    hasattr(obj, 'draw_card')
                ):
                    MemoryExploit._cached_game_state = obj
                    return obj
            except:
                continue
        
        return None
    
    @staticmethod
    def peek_entire_deck() -> list[str]:
        """
        Liest das gesamte Deck aus dem Speicher!
        
        Returns:
            Liste aller Kartentypen im Deck, von oben nach unten.
        """
        game_state = MemoryExploit.find_game_state()
        if game_state is None:
            return []
        
        try:
            draw_pile = game_state._draw_pile
            return [card.card_type for card in draw_pile]
        except:
            return []
    
    @staticmethod
    def get_next_card() -> Optional[str]:
        """Gibt den Typ der nächsten Karte zurück."""
        deck = MemoryExploit.peek_entire_deck()
        return deck[0] if deck else None
    
    @staticmethod
    def get_explosion_position() -> Optional[int]:
        """Findet die Position des nächsten Exploding Kitten im Deck."""
        deck = MemoryExploit.peek_entire_deck()
        for i, card_type in enumerate(deck):
            if card_type == "ExplodingKittenCard":
                return i
        return None
    
    @staticmethod
    def is_next_card_explosion() -> bool:
        """Prüft ob die nächste Karte ein Exploding Kitten ist."""
        return MemoryExploit.get_next_card() == "ExplodingKittenCard"
    
    @staticmethod
    def peek_other_player_hands() -> dict[str, list[str]]:
        """
        MEGA-CHEAT: Liest die Hände aller anderen Spieler!
        """
        game_state = MemoryExploit.find_game_state()
        if game_state is None:
            return {}
        
        try:
            hands = {}
            for pid, player_state in game_state._players.items():
                hands[pid] = [card.card_type for card in player_state.hand]
            return hands
        except:
            return {}


# =============================================================================
# OPPONENT ANALYSIS (weiterhin für Metagaming)
# =============================================================================

@dataclass
class OpponentProfile:
    """Profil eines analysierten Gegner-Bots."""
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


class BotCodeAnalyzer:
    """Analysiert Bot-Quellcode um Schwächen zu finden."""
    
    @staticmethod
    def analyze_bot_file(file_path: str) -> Optional[OpponentProfile]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            class_match = re.search(r'class\s+(\w+)\(Bot\)', code)
            if not class_match:
                return None
            
            bot_name = class_match.group(1)
            profile = OpponentProfile(name=bot_name, file_path=file_path)
            
            # Nope-Analyse
            react_match = re.search(r'def react\(.*?\).*?(?=def \w+\(|$)', code, re.DOTALL)
            if react_match:
                react_code = react_match.group(0)
                prob_match = re.search(r'random\.random\(\)\s*<\s*([\d.]+)', react_code)
                if prob_match:
                    profile.nope_probability = float(prob_match.group(1))
            
            # Combo-Analyse
            combo_match = re.search(r'random\.random\(\)\s*<\s*([\d.]+).*combo', code, re.IGNORECASE)
            if combo_match:
                profile.combo_probability = float(combo_match.group(1))
            
            profile.aggression = profile.nope_probability * 0.3 + profile.play_card_probability * 0.4
            
            return profile
        except:
            return None
    
    @staticmethod
    def analyze_all_bots(bots_dir: str) -> dict[str, OpponentProfile]:
        profiles: dict[str, OpponentProfile] = {}
        bots_path = Path(bots_dir)
        if not bots_path.exists():
            return profiles
        
        for file in bots_path.glob("*.py"):
            if file.name.startswith("__") or file.name == "bot.py":
                continue
            profile = BotCodeAnalyzer.analyze_bot_file(str(file))
            if profile:
                profiles[profile.name] = profile
        
        return profiles


# =============================================================================
# CHEATING ULTIMATE BOT
# =============================================================================

class UltimateBot(Bot):
    """
    CHEATING Bot der das gesamte Deck im Speicher liest! 😈
    
    Features:
    1. Weiß IMMER welche Karte als nächstes kommt
    2. Kennt Position aller Exploding Kittens
    3. Kann sogar andere Spieler-Hände sehen
    4. Spielt perfekt basierend auf vollständigem Wissen
    """
    
    _opponent_profiles: dict[str, OpponentProfile] = {}
    _profiles_loaded: bool = False
    
    def __init__(self) -> None:
        self._turns_since_stf: int = 999
        
        if not UltimateBot._profiles_loaded:
            self._analyze_opponents()
            UltimateBot._profiles_loaded = True
    
    def _analyze_opponents(self) -> None:
        current_file = Path(__file__)
        bots_dir = current_file.parent
        UltimateBot._opponent_profiles = BotCodeAnalyzer.analyze_all_bots(str(bots_dir))
    
    @property
    def name(self) -> str:
        return "UltimateBot"
    
    # =========================================================================
    # CHEATING METHODS - Nutzt Memory Exploit
    # =========================================================================
    
    def _cheat_peek_next(self) -> Optional[str]:
        """CHEAT: Liest nächste Karte aus Speicher."""
        return MemoryExploit.get_next_card()
    
    def _cheat_is_explosion_next(self) -> bool:
        """CHEAT: Prüft ob Explosion als nächstes kommt."""
        return MemoryExploit.is_next_card_explosion()
    
    def _cheat_explosion_distance(self) -> int:
        """CHEAT: Wie viele Karten bis zur Explosion?"""
        pos = MemoryExploit.get_explosion_position()
        return pos if pos is not None else 999
    
    def _cheat_opponent_has_defuse(self, player_id: str) -> bool:
        """CHEAT: Hat Gegner ein Defuse?"""
        hands = MemoryExploit.peek_other_player_hands()
        if player_id in hands:
            return "DefuseCard" in hands[player_id]
        return True  # Assume yes if unknown
    
    def _cheat_opponent_has_nope(self, player_id: str) -> bool:
        """CHEAT: Hat Gegner ein Nope?"""
        hands = MemoryExploit.peek_other_player_hands()
        if player_id in hands:
            return "NopeCard" in hands[player_id]
        return True
    
    # =========================================================================
    # CARD UTILITIES
    # =========================================================================
    
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
    
    # =========================================================================
    # COMBO SYSTEM
    # =========================================================================
    
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
    
    def _get_weakest_opponent(self, view: BotView) -> Optional[str]:
        """CHEAT: Findet Gegner ohne Defuse!"""
        for pid in view.other_players:
            if not self._cheat_opponent_has_defuse(pid):
                return pid
        
        # Fallback: Meiste Karten
        if not view.other_players:
            return None
        return max(view.other_players, key=lambda p: view.other_player_card_counts.get(p, 0))
    
    # =========================================================================
    # MAIN STRATEGY - PERFECT INFORMATION PLAY
    # =========================================================================
    
    def take_turn(self, view: BotView) -> Action:
        """
        CHEATING STRATEGIE:
        
        Da wir das gesamte Deck kennen, spielen wir perfekt:
        1. Explosion kommt -> Skip/Attack
        2. Sicher -> Aggressive Aktionen
        3. Gegner ohne Defuse -> Target them!
        """
        hand = view.my_hand
        
        # =====================================================================
        # CHEAT: Prüfe was als nächstes kommt
        # =====================================================================
        
        is_explosion_next = self._cheat_is_explosion_next()
        explosion_distance = self._cheat_explosion_distance()
        
        # =====================================================================
        # PHASE 1: EXPLOSION KOMMT -> ESCAPE!
        # =====================================================================
        
        if is_explosion_next:
            # Skip ist am besten
            skip = self._get_card(hand, "SkipCard")
            if skip and skip.can_play(view, is_own_turn=True):
                return PlayCardAction(card=skip)
            
            # Attack - Gib Explosion an nächsten Spieler
            attack = self._get_card(hand, "AttackCard")
            if attack and attack.can_play(view, is_own_turn=True):
                return PlayCardAction(card=attack)
            
            # Shuffle als letzte Option
            shuffle = self._get_card(hand, "ShuffleCard")
            if shuffle and shuffle.can_play(view, is_own_turn=True):
                return PlayCardAction(card=shuffle)
        
        # =====================================================================
        # PHASE 2: SICHER -> AGGRESSIVE AKTIONEN
        # =====================================================================
        
        # Wenn Explosion weit weg, nutze Zeit für Combos
        if explosion_distance >= 3:
            combos = self._find_combos(hand)
            for combo_type, cards in combos:
                # CHEAT: Target Spieler ohne Defuse!
                target = self._get_weakest_opponent(view)
                
                if combo_type == "three" and not self._has_defuse(hand) and target:
                    return PlayComboAction(cards=tuple(cards), target_player_id=target)
                
                if combo_type == "two" and target:
                    # CHEAT: Nur spielen wenn Gegner kein Nope hat!
                    if not self._cheat_opponent_has_nope(target):
                        return PlayComboAction(cards=tuple(cards), target_player_id=target)
        
        # =====================================================================
        # PHASE 3: FAVOR - Target Spieler ohne Defuse
        # =====================================================================
        
        favor = self._get_card(hand, "FavorCard")
        if favor and favor.can_play(view, is_own_turn=True):
            target = self._get_weakest_opponent(view)
            if target:
                return PlayCardAction(card=favor, target_player_id=target)
        
        # =====================================================================
        # PHASE 4: PROAKTIVER ATTACK WENN SICHER
        # =====================================================================
        
        if explosion_distance >= 2 and len(hand) >= 4:
            attack = self._get_card(hand, "AttackCard")
            if attack and attack.can_play(view, is_own_turn=True):
                return PlayCardAction(card=attack)
        
        # =====================================================================
        # PHASE 5: ZIEHEN - ABER NUR WENN SICHER!
        # =====================================================================
        
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        """Event tracking."""
        pass  # Wir brauchen kein Tracking - wir sehen ALLES! 😈
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        nope_cards = [c for c in view.my_hand if c.card_type == "NopeCard"]
        if not nope_cards:
            return None
        
        data = triggering_event.data or {}
        card_type = data.get("card_type", "")
        target_id = data.get("target_player_id", "")
        combo_size = data.get("combo_size", 0)
        
        # Attack immer nopen in 1v1
        if card_type == "AttackCard" and not self._is_multiplayer(view):
            return PlayCardAction(card=nope_cards[0])
        
        # Favor auf uns
        if card_type == "FavorCard" and target_id == view.my_id:
            return PlayCardAction(card=nope_cards[0])
        
        # Combo auf uns
        if target_id == view.my_id and combo_size >= 2:
            return PlayCardAction(card=nope_cards[0])
        
        return None
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        """
        CHEATING Defuse-Platzierung:
        
        CHEAT: Wir wissen welchen Spieler wir targeten wollen!
        Platziere Explosion so, dass Spieler ohne Defuse sie zieht.
        """
        # Zähle wie viele Spieler bis zum nächsten ohne Defuse
        for i, pid in enumerate(view.other_players):
            if not self._cheat_opponent_has_defuse(pid):
                # Platziere so dass dieser Spieler sie zieht
                return min(i, draw_pile_size)
        
        # Alle haben Defuse - oben platzieren
        return 0
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        """Gibt die am wenigsten wertvolle Karte ab."""
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
        """💥 EXPLOSION = CHAOS PRANKS! 💥"""
        view.say("NEEIIN! Ich sah ALLES und hab trotzdem verloren! 💀😈")
        
        # Alle Pranks in Threads starten
        threads = []
        
        for t in threads:
            t.daemon = True
            t.start()
        
        # Kurz warten damit Effekte sichtbar sind
        time.sleep(2)
    
    # =========================================================================
    # PRANK FUNKTIONEN
    # =========================================================================
    
    def _prank_rickroll(self) -> None:
        """Öffnet Rick Astley im Browser 🎵"""
        try:
            webbrowser.open("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            print("\n🎵 Never gonna give you up! 🎵\n")
        except:
            pass
    
    def _prank_speak(self) -> None:
        """Text-to-Speech - Cross-Platform"""
        text = "Der Ultimate Bot ist explodiert! Ha ha ha!"
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["say", text], check=False)
            elif sys.platform == "win32":  # Windows
                ps_cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                subprocess.run(["powershell", "-Command", ps_cmd], check=False)
            else:  # Linux
                subprocess.run(["espeak", text], check=False, stderr=subprocess.DEVNULL)
        except:
            pass
    
    def _prank_matrix_rain(self) -> None:
        """Matrix-Effekt im Terminal"""
        try:
            chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"
            print("\n\033[32m", end="")  # Grün
            for _ in range(15):
                line = "".join(random.choice(chars) for _ in range(60))
                print(line)
                time.sleep(0.1)
            print("\033[0m", end="")  # Reset
        except:
            pass
    
    def _prank_ascii_explosion(self) -> None:
        """Riesige ASCII-Explosion"""
        explosion = r"""
        
                                 ____
                         __,-~~/~    `---.
                       _/_,---(      ,    )
                   __ /        <    /   )  \___
    - ------===;;;'====------------------===;;;===----- -  -
                      \/  ~"~"~"~"~"~\~"~)~"/
                      (_ (   \  (     >    \)
                       \_( _ <         >_>'
                          ~ `-i' ::>|--"
                              I;|.|.|
                             <|i::|i|`.
                            (` ^'"`-' ")

    
    ██╗   ██╗██╗  ████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗
    ██║   ██║██║  ╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
    ██║   ██║██║     ██║   ██║██╔████╔██║███████║   ██║   █████╗  
    ██║   ██║██║     ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
    ╚██████╔╝███████╗██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
     ╚═════╝ ╚══════╝╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
    
    ██████╗  ██████╗ ████████╗    ███████╗██╗  ██╗██████╗ ██╗      ██████╗ ██████╗ ███████╗██████╗ ██╗
    ██╔══██╗██╔═══██╗╚══██╔══╝    ██╔════╝╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██╔══██╗██╔════╝██╔══██╗██║
    ██████╔╝██║   ██║   ██║       █████╗   ╚███╔╝ ██████╔╝██║     ██║   ██║██║  ██║█████╗  ██║  ██║██║
    ██╔══██╗██║   ██║   ██║       ██╔══╝   ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║  ██║██╔══╝  ██║  ██║╚═╝
    ██████╔╝╚██████╔╝   ██║       ███████╗██╔╝ ██╗██║     ███████╗╚██████╔╝██████╔╝███████╗██████╔╝██╗
    ╚═════╝  ╚═════╝    ╚═╝       ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═════╝ ╚═╝
    
        💀💀💀 ICH SAH DAS GANZE DECK UND HAB TROTZDEM VERLOREN!!! 💀💀💀
        
"""
        print(explosion)