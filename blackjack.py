import random

class GameState:
    def __init__(self):
        self.shoe = []
        self.shoe_value = 0
        self.players_list = []

        self.max_dealer_hand = 26
        self.max_player_hand = 30
        self.max_players = 5
        self.max_hands = 2

        self.decks = 1
        self.deck_value = 0
        self.buy_in = 1000.00
        self.casino_name = "N3rds Casino"
        self.surrender_allowed = True

        self.deck_list = self.create_deck()
        self.dealer = Player("Dealer", self)

    def create_deck(self):
        base_deck = []
        deck_list = []
        suits = ["♠", "♥", "♣", "♦"]
        ranks = ["A"] + [str(n) for n in range(2, 11)] + ["J", "Q", "K"]
        single_deck_value = 0

        for s in suits:
            for r in ranks:
                base_deck.append(Card(r, s))
                single_deck_value += self.get_card_value(r)

        for _ in range(self.decks):
            deck_list.extend(base_deck)

        self.deck_value = self.decks * single_deck_value
        return deck_list

    def get_card_value(self, rank):
        if rank in "JQK":
            return 10
        elif rank == "A":
            return 1
        return int(rank)

    def display_welcome(self):
        welcome_message = (
            f"\033[94mWelcome to {self.casino_name}! Decks shuffled into the shoe: "
            f"{self.decks}. Max players per table: {self.max_players}. "
            f"Max number of hands per player: {self.max_hands}. "
            f"Surrenders are \033[0m"
        )
        welcome_message += "\033[94mallowed.\033[0m" if self.surrender_allowed else "\033[94mnot allowed.\033[0m"
        print(welcome_message)

    def create_players(self):
        num_players = self.get_num_players()
        for p in range(num_players):
            pname = input(f"What is the name of player {p+1}? ").strip()
            if not pname:
                pname = f"Player {p+1}"
            self.players_list.append(Player(pname, self))

    def get_num_players(self):
        while True:
            try:
                p = int(input(f"Choose the number of players (1-{self.max_players}): "))
                if 1 <= p <= self.max_players:
                    return p
                print("The table can't hold that many players!" if p > self.max_players else "At least one player required.")
            except ValueError:
                print("That's not a valid number.")

    def check_shoe_size(self):
        min_value = self.get_min_shoe()
        while self.shoe_value < min_value:
            print("Dealer adds another deck to the shoe." if self.shoe_value > 0 else "The dealer adds a deck to the shoe.")
            self.shoe_value += self.add_to_shoe()

    def get_min_shoe(self):
        return self.max_dealer_hand + (len(self.players_list) * self.max_hands * self.max_player_hand)

    def add_to_shoe(self):
        new_deck = self.deck_list.copy()
        random.shuffle(new_deck)
        self.shoe = new_deck + self.shoe
        return self.deck_value

    def initial_deal(self):
        self.starter_hands()
        players_to_remove = self.handle_betting()
        self.remove_player(players_to_remove)

        if not self.players_list:
            return

        for _ in range(2):
            for p in self.players_list:
                self.deal_cards(p.hands[0])
            self.deal_cards(self.dealer.hands[0])

        for p in self.players_list:
            p.hands[0].print_hand()
            p.hands[0].check_blackjack()

        self.dealer.show_upcard()
        self.dealer.hands[0].check_blackjack()
        print("-------------------------------------------------")

    def handle_betting(self):
        players_to_remove = []
        for p in self.players_list:
            while p.hands[0].bet == 0:
                binput = input(f"{p.name} has ${p.bankroll}. Bet? Enter 1000 or 'leave' to exit: ")
                p.hands[0].bet = p.betting(binput)
            if p.hands[0].bet == -1:
                players_to_remove.append(p)
            else:
                p.bankroll -= p.hands[0].bet
        return players_to_remove

    def remove_player(self, players):
        for r in players:
            self.players_list.remove(r)

    def starter_hands(self):
        for p in self.players_list:
            p.hands.append(Hand(1, p))
        self.dealer.hands.append(Hand(1, self.dealer))

    def deal_cards(self, hand):
        if not self.shoe:
            self.add_to_shoe()

        new_card = self.shoe.pop()
        hand.cards.append(new_card)
        if new_card.rank == "A":
            hand.soft_aces += 1
        hand.total += new_card.value
        hand.demote_ace()

    def get_yes_or_no(self, message):
        while True:
            p = input(message).lower().strip()
            if p in ("yes", "y", "no", "n"):
                return p
            print("Please answer yes or no.")

    def check_insurance(self):
        for p in self.players_list:
            if p.bankroll >= p.hands[0].bet / 2:
                choice = self.get_yes_or_no(f"Would {p.name} like insurance? ")
                if choice in ("yes", "y"):
                    p.hasInsurance = True
                    p.bankroll -= p.hands[0].bet / 2
            else:
                print(f"{p.name} cannot afford insurance.")

        if self.dealer.hands[0].isBlackjack:
            self.dealer.dealer_blackjack(self)
        else:
            print("Dealer does not have blackjack.")

    def dealer_start_round_checks(self):
        if self.dealer.hands[0].cards[0].rank == "A":
            self.check_insurance()

        if self.dealer.hands[0].isBlackjack:
            if self.dealer.hands[0].cards[0].rank != "A":
                self.dealer.dealer_blackjack(self)
            return False
        return True

    def player_turn(self, player):
        for h in player.hands:
            while not h.locked:
                if h.firstTurn:
                    h.print_hand()
                    if h.isBlackjack:
                        print(f"\033[32m{player.name} has blackjack!\033[0m")
                        h.locked = True
                        break
                    else:
                        self.dealer.show_upcard()

                options = h.create_action_list(self)
                msg = h.create_message(options)
                action = player.get_player_input(options, msg)
                h.resolve_action(action, self)

    def bust_check(self):
        return any(not h.isBust for p in self.players_list for h in p.hands)

    def settle_round(self):
        for p in self.players_list:
            for h in p.hands:
                h.settle(self.dealer)

    def round_cleanup(self):
        players_to_remove = []
        hands_total = 0

        for p in self.players_list:
            for h in p.hands:
                hands_total += h.total

            p.clear_round()

            if p.bankroll < 1:
                choice = self.get_yes_or_no(f"{p.name} is broke. Rebuy? ")
                if choice in ("yes", "y"):
                    print(f"{p.name} rebuys for ${self.buy_in}.")
                    p.bankroll += self.buy_in
                else:
                    print(f"{p.name} leaves the table.")
                    players_to_remove.append(p)

        self.remove_player(players_to_remove)

        hands_total += self.dealer.hands[0].total
        self.dealer.clear_round()

        self.shoe_value -= hands_total


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.card = rank + suit

        if rank == "A":
            self.value = 11
        elif rank in "JQK":
            self.value = 10
        else:
            self.value = int(rank)

    def __str__(self):
        return self.card

    def __repr__(self):
        if self.rank == "A":
            return f"{self.card} value 11 (soft), can be 1."
        return f"{self.card} value {self.value}."


class Player:
    def __init__(self, name, game):
        self.name = name
        self.bankroll = game.buy_in
        self.hands = []
        self.hasInsurance = False

    def betting(self, bet_string):
        bet_string = bet_string.lower().strip()
        if bet_string == "leave":
            print(f"{self.name} leaves with ${self.bankroll}.")
            return -1
        if bet_string.isnumeric():
            bet_amount = int(bet_string)
            if bet_amount > self.bankroll:
                print("Insufficient funds.")
                return 0
            if bet_amount == 0:
                print(f"{self.name} leaves with ${self.bankroll}.")
                return -1
            return bet_amount
        print("Invalid bet.")
        return 0

    def show_upcard(self):
        print(f"Dealer's upcard: {self.hands[0].cards[0]}")

    def dealer_blackjack(self, game):
        game.dealer.hands[0].print_hand()
        print("Dealer has blackjack!")

        for p in game.players_list:
            h = p.hands[0]

            if h.isBlackjack:
                if p.hasInsurance:
                    print(f"{p.name}: blackjack push, insurance pays.")
                    p.bankroll += h.bet * 2.5
                else:
                    print(f"{p.name}: push.")
                    p.bankroll += h.bet
            else:
                if p.hasInsurance:
                    print(f"{p.name}: insurance pays.")
                    p.bankroll += h.bet * 1.5
                else:
                    print(f"{p.name} loses.")

    def get_player_input(self, actions, message):
        while True:
            x = input(message).lower().strip()
            if x in actions:
                return x
            print("Invalid option.")

    def can_split(self, hand, game):
        if self.bankroll < hand.bet:
            print("Not enough funds!")
            return False
        if hand.cards[0].rank != hand.cards[1].rank:
            print("Cannot split.")
            return False
        if len(self.hands) >= game.max_hands:
            print(f"{self.name} cannot have more hands.")
            return False
        return True

    def split(self, current_hand, game):
        if not self.can_split(current_hand, game):
            return

        new_hand = Hand(len(self.hands) + 1, self)
        self.hands.append(new_hand)

        self.bankroll -= current_hand.bet
        new_hand.bet = current_hand.bet

        split_card = current_hand.cards.pop(1)
        new_hand.cards.append(split_card)
        new_hand.total = split_card.value

        if split_card.rank == "A":
            current_hand.soft_aces = 1
            new_hand.soft_aces = 1
            current_hand.total -= 1
        else:
            current_hand.total -= split_card.value

        for h in (current_hand, new_hand):
            game.deal_cards(h)
            h.print_hand()
            h.check_blackjack()

    def dealer_turn(self, game):
        if game.bust_check():
            self.hands[0].print_hand()
            while not self.hands[0].locked:
                if self.hands[0].total < 17:
                    print("Dealer hits.")
                    self.hands[0].hit(game)
                else:
                    self.hands[0].stand()

    def clear_round(self):
        self.hasInsurance = False
        self.hands = []

    def __str__(self):
        return self.name


class Hand:
    def __init__(self, id, player):
        self.player = player
        self.id = id
        self.cards = []
        self.total = 0
        self.soft_aces = 0
        self.bet = 0
        self.locked = False
        self.firstTurn = True
        self.isBlackjack = False
        self.isBust = False

    def demote_ace(self):
        while self.total > 21 and self.soft_aces:
            self.total -= 10
            self.soft_aces -= 1

    def check_blackjack(self):
        if self.total == 21 and len(self.cards) == 2:
            self.isBlackjack = True

    def print_hand(self):
        if len(self.player.hands) > 1:
            print(f"{self.player.name}'s hand {self.id}: {self}")
        else:
            print(f"{self.player.name}'s hand: {self}")

    def create_action_list(self, game):
        actions = ["hit", "stand"]

        if self.firstTurn and self.player.bankroll >= self.bet:
            if len(self.cards) == 2 and self.cards[0].rank == self.cards[1].rank:
                if len(self.player.hands) < game.max_hands:
                    actions.append("split")
            actions.append("double")

        if self.firstTurn and game.surrender_allowed:
            actions.append("surrender")

        return actions

    def create_message(self, valid_actions):
        if len(self.player.hands) > 1:
            base = f"Will {self.player.name}, for hand {self.id}, "
        else:
            base = f"Will {self.player.name} "

        if len(valid_actions) == 1:
            return base + f"{valid_actions[0]}? "

        return base + ", ".join(valid_actions[:-1]) + f", or {valid_actions[-1]}? "

    def resolve_action(self, action, game):
        if self.firstTurn and action != "split":
            self.firstTurn = False

        if action == "hit":
            print(f"{self.player.name} hits.")
            self.hit(game)

        elif action == "stand":
            self.stand()

        elif action == "double":
            print(f"{self.player.name} doubles down!")
            self.doubling(game)

        elif action == "split":
            self.player.split(self, game)

        elif action == "surrender":
            print(f"{self.player.name} surrenders.")
            self.surrender()

    def hit(self, game):
        game.deal_cards(self)
        self.print_hand()

        if self.player.name != "Dealer":
            if self.total > 21:
                self.isBust = True
                self.locked = True
                print(f"\033[31m{self.player.name} busts!\033[0m")
            elif self.total == 21:
                self.stand()
        else:
            if self.total > 21:
                self.isBust = True
                self.locked = True
                print("\033[32mDealer busts! Players win!\033[0m")
            elif self.total >= 17:
                self.stand()

    def doubling(self, game):
        self.player.bankroll -= self.bet
        self.bet *= 2
        self.hit(game)
        if self.total < 21:
            self.stand()

    def surrender(self):
        self.player.bankroll += self.bet / 2
        self.bet /= 2
        self.locked = True
        self.isBust = True

    def stand(self):
        print(f"\033[34m{self.player.name} stands at {self.total}.\033[0m")
        self.locked = True

    def settle(self, dealer):
        self.print_hand()
        dhand = dealer.hands[0]

        if dhand.isBust and not self.isBust:
            if self.isBlackjack:
                print(f"{self.player.name} wins with blackjack! +${self.bet * 1.5}")
                self.blackjack()
            else:
                print(f"{self.player.name} wins ${self.bet}!")
                self.win()

        elif not self.isBust:
            if self.total > dhand.total:
                if self.isBlackjack:
                    print(f"{self.player.name} wins with blackjack! +${self.bet * 1.5}")
                    self.blackjack()
                else:
                    print(f"{self.player.name} wins ${self.bet}!")
                    self.win()

            elif self.total == dhand.total:
                print(f"{self.player.name} pushes.")
                self.push()

            else:
                print(f"{self.player.name} loses ${self.bet}.")

        else:
            print(f"{self.player.name} loses ${self.bet}.")

    def blackjack(self):
        self.player.bankroll += self.bet * 2.5

    def win(self):
        self.player.bankroll += self.bet * 2

    def push(self):
        self.player.bankroll += self.bet

    def __str__(self):
        return " ".join(str(c) for c in self.cards)


# ------------------------------
# START GAME
# ------------------------------

game_state = GameState()
game_state.display_welcome()
game_state.create_players()

while game_state.players_list:
    game_state.check_shoe_size()
    game_state.initial_deal()

    if not game_state.players_list:
        break

    if game_state.dealer_start_round_checks():
        for p in game_state.players_list:
            game_state.player_turn(p)

        game_state.dealer.dealer_turn(game_state)
        game_state.settle_round()

    game_state.round_cleanup()
