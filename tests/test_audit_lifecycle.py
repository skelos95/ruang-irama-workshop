"""Execute source-derived bookkeeping and dispatch for sustained lobby churn.

These tests project roster arrays, icon ownership, votes, and scheduler calls.
They do not emulate Overwatch entity lifetime, input delivery, or engine physics.
"""

import copy
import operator
import re
import unittest

from tools import validate_workshop as validator
from tools import check_clipboard_import as clipboard
from tests.test_fly_motion import Expression
from tests.test_roster_rejoin_regressions import LifecycleSourceEvaluator, SOURCES


class AuditExpression(Expression):
    TOKEN = re.compile(Expression.TOKEN.pattern + r"|%")
    PRECEDENCE = {**Expression.PRECEDENCE, "%": 3}


def arguments(text):
    depth = 0
    start = 0
    values = []
    for index, character in enumerate(text):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth -= 1
        elif character == "," and depth == 0:
            values.append(text[start:index].strip())
            start = index + 1
    values.append(text[start:].strip())
    return values


def statements(source):
    """Parse If/Else/For blocks before projecting away unrelated engine actions."""
    tokens = [part.strip() for part in validator.mask_strings(source).split(";") if part.strip()]

    def parse(index):
        result = []
        while index < len(tokens) and tokens[index] not in ("Else", "End"):
            token = tokens[index]
            index += 1
            if token.startswith(("If(", "For Global Variable(")):
                body, index = parse(index)
                otherwise = []
                if index < len(tokens) and tokens[index] == "Else":
                    otherwise, index = parse(index + 1)
                if index >= len(tokens) or tokens[index] != "End":
                    raise AssertionError("unterminated source block")
                index += 1
                result.append((token, body, otherwise))
            else:
                result.append((token, None, None))
        return result, index

    result, consumed = parse(0)
    if consumed != len(tokens):
        raise AssertionError("unexpected source End/Else")
    return result


def project(nodes, keep):
    result = []
    for token, body, otherwise in nodes:
        if body is None:
            if keep(token):
                result.append((token, None, None))
        else:
            selected = project(body, keep)
            alternative = project(otherwise, keep)
            if selected or alternative:
                result.append((token, selected, alternative))
    return result


class AuditLifecycleEvaluator(LifecycleSourceEvaluator):
    ICONS = {"IkonKebalPemain": "IkonKebal", "IkonKartuNasibPemain": "IkonKartuNasib"}
    FIELDS = {"PemainDipilih", "JumlahPilihan", "NamaTampilan", "WarnaNama"}

    def __init__(self, source):
        if re.search(r'(?m)^regola\(', source):
            segments = re.split(r'("(?:\\.|[^"\\])*")', source)
            for index in range(0, len(segments), 2):
                for original, translated in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
                    segments[index] = clipboard._replace_token(segments[index], original, translated)
            source = "".join(segments)
        super().__init__(source)
        self.current = None
        self.calls = []
        self.lock_at_bot_call = []
        self.initializers = "\n".join(validator.mask_strings(rule.body) for rule in self.rules)
        for name in self.ICONS:
            match = re.search(rf"Global\.{name} = (Array\([^;]+\));", self.initializers)
            if match is not None:
                self.globals[name] = self.evaluate(match.group(1))
        self.vote = validator.rule_block(validator.rule_by_subroutine(self.rules, "HitungPilihan"), "actions")
        self.cleanup_program = project(statements(self.cleanup), self.keep_cleanup)

    def resolve(self, name):
        if name == "CurrentArrayElement":
            return self.current
        if name in self.FIELDS:
            return name
        if name == "EmptyArray":
            return []
        if name == "AllTeams":
            return "all-teams"
        if name.startswith("EventPlayer."):
            return self.players.get(self.event_player, {}).get(name.split(".", 1)[1])
        if name.startswith("Global.") and len(name.split(".")) == 3:
            _, owner, field = name.split(".")
            return self.players.get(self.globals[owner], {}).get(field)
        return super().resolve(name)

    def call(self, name, args):
        if name == "Array":
            return list(args)
        if name == "PlayerVariable":
            return self.players.get(args[0], {}).get(args[1])
        if name == "CustomString":
            return ""
        if name == "CustomColor":
            return tuple(args)
        if name == "AllPlayers":
            return [identity for identity, state in self.players.items() if state.get("exists")]
        if name == "IsAlive":
            return self.players.get(args[0], {}).get("alive", False)
        if name == "LastOf":
            return args[0][-1]
        return super().call(name, args)

    def evaluate(self, expression):
        packed = re.sub(r"\s+", "", expression)
        while "[" in packed:
            converted = re.sub(r"([A-Za-z_][\w.]*)\[([^\[\]]+)\]", r"At(\1,\2)", packed)
            if converted == packed:
                raise AssertionError(f"unsupported array access: {expression}")
            packed = converted
        tree = AuditExpression(packed).tree
        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                      "/": operator.truediv, "%": operator.mod, "==": operator.eq,
                      "!=": operator.ne, "<": operator.lt, ">": operator.gt,
                      "<=": operator.le, ">=": operator.ge}

        def visit(node):
            kind = node[0]
            if kind == "literal":
                return node[1]
            if kind == "name":
                return self.resolve(node[1])
            if kind == "negate":
                return -visit(node[1])
            if kind != "call":
                return operations[kind](visit(node[1]), visit(node[2]))
            name, args = node[1:]
            if name in ("And", "Or"):
                return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
            if name in ("FilteredArray", "SortedArray"):
                values = visit(args[0])
                previous = self.current

                def key(value):
                    self.current = value
                    return visit(args[1])

                try:
                    return [value for value in values if key(value)] if name == "FilteredArray" else sorted(values, key=key)
                finally:
                    self.current = previous
            return self.call(name, [visit(arg) for arg in args])

        return visit(tree)

    def execute(self, nodes):
        for token, body, otherwise in nodes:
            if token.startswith("If("):
                branch = body if self.evaluate(token[3:-1]) else otherwise
                if self.execute(branch):
                    return True
            elif token.startswith("For Global Variable("):
                name, first, last, step = arguments(token[len("For Global Variable("):-1])
                for index in range(int(self.evaluate(first)), int(self.evaluate(last)), int(self.evaluate(step))):
                    self.globals[name] = index
                    if self.execute(body):
                        return True
            elif token == "Abort":
                return True
            elif token.startswith("Destroy Icon("):
                self.destroyed.append(self.evaluate(token[len("Destroy Icon("):-1]))
            elif token.startswith("Modify Global Variable("):
                name, operation, index = arguments(token[len("Modify Global Variable("):-1])
                if operation != "Remove From Array By Index":
                    raise AssertionError(f"unsupported global mutation: {token}")
                self.globals[name].pop(int(self.evaluate(index)))
            elif token.startswith("Set Player Variable("):
                target, field, value = arguments(token[len("Set Player Variable("):-1])
                identities = self.evaluate(target)
                identities = identities if isinstance(identities, list) else [identities]
                result = self.evaluate(value)
                for identity in identities:
                    self.players[identity][field] = result
            elif token.startswith("Call Subroutine("):
                name = token[len("Call Subroutine("):-1]
                self.calls.append((self.globals.get("PemainAktif"), name))
                if name == "HitungPilihan":
                    self.execute(statements(self.vote))
                elif name == "KunciBot":
                    self.lock_at_bot_call.append(self.globals["PemainSiklusGlobal"])
            elif re.match(r"(?:Global\.|Event Player\.)[^=]+=(?!=)", token):
                self.execute_assignment(token)
            else:
                raise AssertionError(f"unsupported projected source statement: {token}")
        return False

    def keep_cleanup(self, token):
        indices = "PemainPembersihan|IndeksKeluar|IndeksPembersihan|IndeksUtangKeluar|SlotHUDTersedia"
        return bool(
            re.match(rf"Global\.({indices}) =", token)
            or token.startswith("Modify Global Variable(")
            or token.startswith("Destroy Icon(")
            or re.match(r"Global\.Ikon(?:Kebal|KartuNasib)Pemain\[", token)
            or re.match(r"(?:Global\.PemainPembersihan|Event Player)\.Ikon(?:Kebal|KartuNasib) =", token)
            or (token.startswith("Set Player Variable(Filtered Array(") and ", PemainDipilih, Null)" in token)
            or token == "Call Subroutine(HitungPilihan)"
        )

    def join(self, identity):
        admitted = super().join(identity)
        if admitted:
            self.players[identity].update(PemainDipilih=None, JumlahPilihan=0, NamaTampilan=identity,
                                          WarnaNama=(255, 255, 255, 255), alive=True)
        return admitted

    def install_icons(self, identity, number):
        self.event_player = identity
        self.globals["PemainAktif"] = identity
        expected = []
        for offset, (array, field) in enumerate(self.ICONS.items()):
            handle = number * 10 + offset + 1
            self.players[identity][field] = handle
            match = re.search(rf"Global\.{array}\[[^;]+\] = (?:Event Player|Global\.PemainAktif)\.{field};", self.initializers)
            if match is None:
                raise AssertionError(f"source does not persist {field} in canonical slots")
            self.execute_assignment(match.group(0).rstrip(";"))
            expected.append(handle)
        return expected

    def remove(self, identity):
        self.event_player = identity
        self.execute(self.cleanup_program)

    def scheduler_tick(self, tick):
        scheduler = next(rule for rule in self.rules if rule.name.startswith("04g -"))
        actions = validator.rule_block(scheduler, "actions")
        keep = lambda token: (
            token.startswith("Call Subroutine(")
            or re.match(r"Global\.(PemainAktif|SalinanDaftarPemain|PemainSiklusGlobal|WaktuSiklusGlobal) =", token)
        )
        self.globals["LangkahPenjadwal"] = tick
        self.execute(project(statements(actions), keep))


class AuditLifecycleTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, AuditLifecycleEvaluator(path.read_text(encoding="utf-8"))

    def assert_roster(self, model, expected_count):
        self.assertTrue(all(len(model.globals[name]) == expected_count for name in model.ARRAYS))
        occupied = model.globals["SlotHUDPemain"]
        available = model.globals["SlotHUDTersedia"]
        self.assertEqual(sorted(occupied + available), list(range(12)))
        self.assertEqual(len(set(occupied)), expected_count)
        self.assertEqual(len(set(model.globals["PemainManusia"])), expected_count)

    def test_240_distinct_players_recycle_all_twelve_slots_with_lost_local_state(self):
        for source, model in self.models():
            with self.subTest(source=source):
                active = []
                handles = {}
                for number in range(240):
                    identity = f"player-{number}"
                    if len(active) == 12:
                        departed = active.pop(0)
                        freed = model.globals["SlotHUDPemain"][model.globals["PemainManusia"].index(departed)]
                        model.players[departed] = {"exists": False}
                        before_destroyed = len(model.destroyed)
                        model.remove(departed)
                        self.assertCountEqual(model.destroyed[before_destroyed:], handles[departed])
                        self.assertEqual(model.globals["SlotHUDTersedia"], [freed])
                        for array in model.ICONS:
                            self.assertFalse(model.globals[array][int(freed)])
                    self.assertTrue(model.join(identity))
                    self.assertFalse(model.join(identity))
                    handles[identity] = model.install_icons(identity, number)
                    active.append(identity)
                    self.assert_roster(model, len(active))
                    if number >= 12:
                        snapshot = copy.deepcopy(model.globals)
                        previous_destroyed = list(model.destroyed)
                        model.remove(departed)
                        # Cleanup scratch is allowed to change; ownership and resources are not.
                        for key in model.ARRAYS + ("SlotHUDTersedia",) + tuple(model.ICONS):
                            self.assertEqual(model.globals[key], snapshot[key])
                        self.assertEqual(model.destroyed, previous_destroyed)
                self.assertFalse(model.join("overflow"))
                for departed in active:
                    model.players[departed] = {"exists": False}
                    model.remove(departed)
                self.assert_roster(model, 0)
                self.assertEqual(model.globals["SlotHUDTersedia"], list(range(12)))
                self.assertEqual(len(model.destroyed), 480)
                self.assertEqual(len(set(model.destroyed)), 480)
                for array in model.ICONS:
                    self.assertEqual(len(model.globals[array]), 12)
                    self.assertFalse(any(model.globals[array]))

    def test_lost_departing_vote_is_rebuilt_from_surviving_owners(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for identity in ("alice", "bob", "carol", "departed"):
                    model.join(identity)
                model.players["alice"]["PemainDipilih"] = "departed"
                model.players["carol"]["PemainDipilih"] = "bob"
                model.players["departed"]["PemainDipilih"] = "bob"
                model.players["bob"]["JumlahPilihan"] = 2
                model.players["departed"]["JumlahPilihan"] = 1
                model.players["departed"] = {"exists": False}
                model.remove("departed")
                self.assertIsNone(model.players["alice"]["PemainDipilih"])
                self.assertEqual(model.players["bob"]["JumlahPilihan"], 1)
                self.assertEqual(model.globals["PemimpinPilihan"], "bob")
                model.players["carol"] = {"exists": False}
                model.remove("carol")
                self.assertEqual(model.players["bob"]["JumlahPilihan"], 0)
                self.assertIsNone(model.globals["PemimpinPilihan"])

    def test_luck_reset_then_leave_does_not_destroy_an_icon_reused_by_another_player(self):
        for source, model in self.models():
            for routine in ("PulihkanNasibPemain", "PulihkanNasibAktif"):
                with self.subTest(source=source, routine=routine):
                    model.join("alice")
                    model.join("bob")
                    model.install_icons("alice", 50)
                    old_handle = model.players["alice"]["IkonKartuNasib"]
                    model.event_player = "alice"
                    model.globals["PemainAktif"] = "alice"
                    rule = validator.rule_by_subroutine(model.rules, routine)
                    actions = validator.rule_block(rule, "actions")
                    keep = lambda token: (
                        token.startswith("Destroy Icon(")
                        or re.match(r"(?:Event Player|Global\.PemainAktif)\.IkonKartuNasib =", token)
                        or token.startswith("Global.IkonKartuNasibPemain[")
                    )
                    before = len(model.destroyed)
                    model.execute(project(statements(actions), keep))
                    self.assertEqual(model.destroyed[before:], [old_handle])
                    alice_slot = model.players["alice"]["UrutanHUD"]
                    bob_slot = model.players["bob"]["UrutanHUD"]
                    self.assertEqual(model.globals["IkonKartuNasibPemain"][alice_slot], 0)
                    # Model a recycled engine ID now owned by a different player.
                    model.players["bob"]["IkonKartuNasib"] = old_handle
                    model.globals["IkonKartuNasibPemain"][bob_slot] = old_handle
                    model.players["alice"] = {"exists": False}
                    before = len(model.destroyed)
                    model.remove("alice")
                    self.assertNotIn(old_handle, model.destroyed[before:])
                    self.assertEqual(model.globals["IkonKartuNasibPemain"][bob_slot], old_handle)
                    model.remove("bob")

    def test_pending_dead_bot_does_not_starve_runtime_of_ready_players(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.players["dead-bot"] = {"exists": True, "spawned": True, "alive": False, "BotOtomatis": True}
                for identity in ("alice", "bob"):
                    model.join(identity)
                model.globals["PemainSiklusGlobal"] = "dead-bot"
                for tick in range(1, 21):
                    model.scheduler_tick(tick)
                for identity in ("alice", "bob"):
                    for routine, expected in (("ProsesCepatPemain", 20), ("ProsesNasibPemain", 20),
                                              ("ProsesTerbangPemain", 20), ("ProsesSiklusPemain", 10),
                                              ("ProsesSimpananPemain", 1)):
                        self.assertEqual(model.calls.count((identity, routine)), expected, (source, identity, routine))

    def test_bot_classifier_releases_only_its_own_reservation_before_engine_lock(self):
        for source, model in self.models():
            for owner in ("dead-bot", "other-player"):
                with self.subTest(source=source, owner=owner):
                    model.event_player = "dead-bot"
                    model.players["dead-bot"] = {"exists": True, "spawned": True, "alive": False,
                                                  "BotOtomatis": True, "SiklusPemainAktif": True,
                                                  "PindahTimDiproses": True}
                    model.globals["PemainSiklusGlobal"] = owner
                    model.now = 5
                    tree = statements(model.classifier)
                    branch = next(node for node in tree if node[0] == "If(Event Player.BotOtomatis == True)")
                    keep = lambda token: token.startswith(("Global.", "Event Player.", "Call Subroutine(")) or token == "Abort"
                    model.execute(project([branch], keep))
                    expected = None if owner == "dead-bot" else owner
                    self.assertEqual(model.globals["PemainSiklusGlobal"], expected)
                    self.assertEqual(model.lock_at_bot_call[-1], expected)
                    self.assertFalse(model.players["dead-bot"]["SiklusPemainAktif"])
                    self.assertFalse(model.players["dead-bot"]["PindahTimDiproses"])


if __name__ == "__main__":
    unittest.main()
