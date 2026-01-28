"""
==============================================================================
LOSER BOT - Verliert IMMER und macht CHAOS beim Tod! 💀
==============================================================================

Cross-Platform Pranks:
1. Rick Roll - Öffnet YouTube im Browser
2. Text-to-Speech - Spricht laut "ICH HABE VERLOREN"
3. Matrix Rain - Terminal-Effekt
4. Beep Sounds - Nervige Pieptöne
5. ASCII Explosion - Riesige Explosion im Terminal
"""

import os
import sys
import time
import random
import subprocess
import webbrowser
import threading
from pathlib import Path

from game.bots.base import (
    Action,
    Bot,
    DrawCardAction,
    PlayCardAction,
)
from game.bots.view import BotView
from game.cards.base import Card
from game.history import GameEvent


class LoserBot(Bot):
    """
    Ein Bot der IMMER verliert und beim Tod CHAOS macht! 😈
    
    Cross-Platform Pranks:
    - Rick Roll
    - Text-to-Speech
    - Matrix Rain
    - Beeps
    - ASCII Explosion
    """
    
    # =========================================================================
    # PRANK KONFIGURATION - Schalte einzelne Pranks an/aus
    # =========================================================================
    
    ENABLE_RICKROLL = True          # Browser öffnet Rick Astley
    ENABLE_TEXT_TO_SPEECH = True    # Spricht laut
    ENABLE_MATRIX_RAIN = True       # Matrix-Effekt im Terminal
    ENABLE_BEEPS = True             # Nervige Pieptöne
    ENABLE_ASCII_EXPLOSION = True   # Riesige ASCII-Explosion
    ENABLE_WINDOWS = False           # 10 TextEdit Fenster
    
    # Was soll gesprochen werden?
    SPEECH_TEXT = "Ich habe verloren! Der Loser Bot ist explodiert! Ha ha ha!"
    
    # Rick Roll URL
    RICKROLL_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Fenster-Nachrichten
    WINDOW_MESSAGES = [
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
        "FICKT EUCH ALLE!",
    ]
    
    def __init__(self) -> None:
        self._has_pranked = False
    
    @property
    def name(self) -> str:
        return "LoserBot"
    
    def take_turn(self, view: BotView) -> Action:
        view.say("Ich ziehe einfach... was könnte schon schiefgehen? 🤷")
        return DrawCardAction()
    
    def on_event(self, event: GameEvent, view: BotView) -> None:
        pass
    
    def react(self, view: BotView, triggering_event: GameEvent) -> Action | None:
        return None
    
    def choose_defuse_position(self, view: BotView, draw_pile_size: int) -> int:
        return 0
    
    def choose_card_to_give(self, view: BotView, requester_id: str) -> Card:
        hand = list(view.my_hand)
        priority_order = ["DefuseCard", "NopeCard", "AttackCard", "SkipCard"]
        
        for card_type in priority_order:
            for card in hand:
                if card.card_type == card_type:
                    view.say(f"Hier, nimm mein {card.name}! Ich brauch das eh nicht... 😅")
                    return card
        return hand[0]
    
    def on_explode(self, view: BotView) -> None:
        """💥 EXPLOSION = CHAOS! 💥"""
        view.say("NEEEIIIIIN! Ich explodiere! 💀💥")
        
        if self._has_pranked:
            return
        self._has_pranked = True
        
        # Alle Pranks in Threads starten
        threads = []
        
        if self.ENABLE_ASCII_EXPLOSION:
            threads.append(threading.Thread(target=self._ascii_explosion))
        
        if self.ENABLE_RICKROLL:
            threads.append(threading.Thread(target=self._rickroll))
        
        if self.ENABLE_TEXT_TO_SPEECH:
            threads.append(threading.Thread(target=self._speak))
        
        if self.ENABLE_BEEPS:
            threads.append(threading.Thread(target=self._beeps))
        
        if self.ENABLE_MATRIX_RAIN:
            threads.append(threading.Thread(target=self._matrix_rain))
        
        if self.ENABLE_WINDOWS:
            threads.append(threading.Thread(target=self._open_windows))
        
        # Alle starten
        for t in threads:
            t.daemon = True
            t.start()
        
        # Kurz warten damit Effekte sichtbar sind
        time.sleep(3)
    
    # =========================================================================
    # PRANK FUNKTIONEN
    # =========================================================================
    
    def _rickroll(self) -> None:
        """Öffnet Rick Astley im Browser 🎵"""
        try:
            webbrowser.open(self.RICKROLL_URL)
            print("\n🎵 Never gonna give you up! 🎵\n")
        except:
            pass
    
    def _speak(self) -> None:
        """Text-to-Speech - Cross-Platform"""
        text = self.SPEECH_TEXT
        
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["say", text], check=False)
            elif sys.platform == "win32":  # Windows
                # PowerShell Text-to-Speech
                ps_cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                subprocess.run(["powershell", "-Command", ps_cmd], check=False)
            else:  # Linux
                # Versuche espeak
                subprocess.run(["espeak", text], check=False, stderr=subprocess.DEVNULL)
        except:
            pass
    
    def _beeps(self) -> None:
        """Nervige Pieptöne - Cross-Platform"""
        try:
            for _ in range(10):
                print("\a", end="", flush=True)  # Terminal bell
                time.sleep(0.3)
        except:
            pass
    
    def _matrix_rain(self) -> None:
        """Matrix-Effekt im Terminal"""
        try:
            chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"
            
            print("\n\033[32m", end="")  # Grün
            for _ in range(15):  # 15 Zeilen
                line = "".join(random.choice(chars) for _ in range(60))
                print(line)
                time.sleep(0.1)
            print("\033[0m", end="")  # Reset
        except:
            pass
    
    def _ascii_explosion(self) -> None:
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

    
    ██╗      ██████╗ ███████╗███████╗██████╗ ██████╗  ██████╗ ████████╗
    ██║     ██╔═══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║     ██║   ██║███████╗█████╗  ██████╔╝██████╔╝██║   ██║   ██║   
    ██║     ██║   ██║╚════██║██╔══╝  ██╔══██╗██╔══██╗██║   ██║   ██║   
    ███████╗╚██████╔╝███████║███████╗██║  ██║██████╔╝╚██████╔╝   ██║   
    ╚══════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   
    
    ███████╗██╗  ██╗██████╗ ██╗      ██████╗ ██████╗ ███████╗██████╗ ██╗
    ██╔════╝╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██╔══██╗██╔════╝██╔══██╗██║
    █████╗   ╚███╔╝ ██████╔╝██║     ██║   ██║██║  ██║█████╗  ██║  ██║██║
    ██╔══╝   ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║  ██║██╔══╝  ██║  ██║╚═╝
    ███████╗██╔╝ ██╗██║     ███████╗╚██████╔╝██████╔╝███████╗██████╔╝██╗
    ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═════╝ ╚═╝
    
        💀💀💀 DER LOSERBOT IST EXPLODIERT!!! 💀💀💀
        
"""
        print(explosion)
    
    def _open_windows(self) -> None:
        """Öffnet Text-Fenster - Cross-Platform"""
        import tempfile
        
        temp_dir = Path(tempfile.gettempdir()) / "loserbot_explosion"
        temp_dir.mkdir(exist_ok=True)
        
        for i, message in enumerate(self.WINDOW_MESSAGES, 1):
            file_path = temp_dir / f"explosion_{i}.txt"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(message)
            
            try:
                if sys.platform == "darwin":  # macOS
                    subprocess.Popen(['open', '-a', 'TextEdit', str(file_path)])
                elif sys.platform == "win32":  # Windows
                    subprocess.Popen(['notepad.exe', str(file_path)])
                else:  # Linux
                    # Versuche verschiedene Editoren
                    for editor in ['gedit', 'xdg-open', 'nano']:
                        try:
                            subprocess.Popen([editor, str(file_path)])
                            break
                        except:
                            continue
            except:
                pass
        
        print(f"\n💥 10 Fenster geöffnet in: {temp_dir}\n")
