"""Mutation checks on the runtime gate, independently of specification tests."""
import unittest
from tools import validate_global_runtime as gate


MINIMAL = '''variables
{
 global:
  0: PemainPemicu
  1: PemainAktif
  2: AntreanPeristiwa
 player:
  0: WarnaNama
}
subroutines
{
 0: Gambar
}
rule("04g - Penjadwal")
{
 event
 {
  Ongoing - Global;
 }
 conditions
 {
  True == True;
 }
 actions
 {
  Global.PemainPemicu = Null;
  Global.PemainAktif = Null;
  Wait(0.050, Ignore Condition);
  Loop;
 }
}
rule("Gambar")
{
 event
 {
  Subroutine; Gambar;
 }
 actions
 {
  Create HUD Text(Evaluate Once(Global.PemainPemicu), Null, Null, Custom String("OK"), Left, 1, Color(White), Color(White), Player Variable(Evaluate Once(Global.PemainPemicu), WarnaNama), Visible To String and Color, Default Visibility);
 }
}
rule("Catat")
{
 event
 {
  Player Died; All; All;
 }
 actions
 {
  Global.AntreanPeristiwa = Array(Event Player, Attacker);
 }
}
'''


def italian_minimal():
    source = MINIMAL
    for old, new in (
        ("variables", "variabili"), (" global:", " globale:"),
        (" player:", " giocatore:"), ("subroutines", "subroutine"),
        ('rule("', 'regola("'), (" event\n", " evento\n"),
        (" conditions\n", " condizioni\n"), (" actions\n", " azioni\n"),
        ("Global.", "Globale."), ("Ignore Condition", "Ignora condizione"),
        ("Color(White)", "Color(Bianco)"), ("Player Died; All; All;", "Player Died; Tutti; Tutti;"),
    ):
        source = source.replace(old, new)
    return source


class GlobalRuntimeGateTests(unittest.TestCase):
    def reject(self, source, fragment):
        errors = gate.validate_runtime(source)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_minimal_global_program_with_record_only_callback_is_valid(self):
        self.assertEqual(gate.validate_runtime(MINIMAL), [])

    def test_each_player_controller_cannot_return(self):
        self.reject(MINIMAL.replace("Subroutine; Gambar;", "Ongoing - Each Player; All; All;"),
                    "Each Player vietato")

    def test_cleanup_cannot_be_executed_in_native_callback(self):
        self.reject(MINIMAL.replace("Global.AntreanPeristiwa = Array(Event Player, Attacker);",
                                    "Destroy HUD Text(10);"), "deve solo registrare")

    def test_callback_cannot_call_subroutine(self):
        self.reject(MINIMAL.replace("Global.AntreanPeristiwa = Array(Event Player, Attacker);",
                                    "Call Subroutine(Gambar);"), "deve solo registrare")

    def test_callback_cannot_mutate_shared_actor(self):
        self.reject(MINIMAL.replace("Global.AntreanPeristiwa =", "Global.PemainPemicu ="),
                    "attore dello scheduler condiviso")

    def test_callback_cannot_set_player_state(self):
        self.reject(MINIMAL.replace("Global.AntreanPeristiwa = Array(Event Player, Attacker);",
                                    "Event Player.WarnaNama = Color(White);"),
                    "deve solo registrare")

    def test_owner_pointer_cannot_be_reevaluated_after_scheduler_advances(self):
        self.reject(MINIMAL.replace("Player Variable(Evaluate Once(Global.PemainPemicu), WarnaNama)",
                                    "Global.PemainPemicu.WarnaNama"), "proprietario non congelato")

    def test_freezing_identity_allows_dynamic_color(self):
        self.assertEqual(gate.unfrozen_actors(
            "Player Variable(Evaluate Once(Global.PemainPemicu), WarnaNama)"), [])

    def test_freezing_other_subexpression_does_not_freeze_owner(self):
        self.assertEqual(gate.unfrozen_actors(
            "Array(Evaluate Once(1), Global.PemainPemicu.WarnaNama)"),
            ["Global.PemainPemicu"])

    def test_shared_actor_must_be_cleared_before_wait(self):
        self.reject(MINIMAL.replace("Global.PemainPemicu = Null;", "Global.PemainPemicu = Host Player;"),
                    "svuotato prima del Wait")

    def test_no_subroutine_wait_even_with_frozen_owner(self):
        self.reject(MINIMAL.replace('Create HUD Text(', 'Wait(0.050, Ignore Condition);\n  Create HUD Text(', 1),
                    "solo lo scheduler può attendere")

    def test_async_rule_can_never_inherit_mutable_actor(self):
        self.reject(MINIMAL.replace("Global.PemainPemicu = Null;", "Start Rule(Gambar, Do Nothing);\n  Global.PemainPemicu = Null;"),
                    "avvio asincrono")

    def test_native_attacker_is_not_available_in_global_renderer(self):
        self.reject(MINIMAL.replace('Custom String("OK")', 'Hero Icon String(Hero Of(Attacker))'),
                    "valore nativo evento non catturato")

    def test_references_to_missing_player_fields_fail(self):
        self.reject(MINIMAL.replace("Global.PemainPemicu = Null;", "Global.PemainPemicu.NonDichiarata = True;\n  Global.PemainPemicu = Null;"),
                    "player non dichiarato")

    def test_variable_indices_stay_within_native_capacity(self):
        self.reject(MINIMAL.replace("2: AntreanPeristiwa", "128: AntreanPeristiwa"), "oltre 128 slot")

    def test_callback_cannot_corrupt_another_scheduler_field(self):
        source = MINIMAL.replace("2: AntreanPeristiwa", "2: AntreanPeristiwa\n  3: IndeksPemainGlobal")
        self.reject(source.replace("Global.AntreanPeristiwa =", "Global.IndeksPemainGlobal ="),
                    "scrittura fuori dalla coda")

    def test_quoted_event_words_are_not_runtime_context(self):
        source = MINIMAL.replace('Custom String("OK")', 'Custom String("Event Player Attacker Victim")')
        self.assertEqual(gate.validate_runtime(source), [])

    def test_hyphenated_native_action_cannot_become_subtraction(self):
        source = MINIMAL.replace("Global.PemainPemicu = Null;", "(Create In - World Text(Host Player, Null, Vector(0, 0, 0), 1, Do Not Clip, Visible To, Color(White), Default Visibility));\n  Global.PemainPemicu = Null;")
        self.reject(source, "azione convertita in espressione")

    def test_italian_normalization_cannot_hide_partial_native_translations(self):
        source = italian_minimal()
        extra = """Globale.AntreanPeristiwa = All Players(All Teams);
  For Global Variable(AntreanPeristiwa, 0, 1, 1); End;
  If(Is True For All(Empty Array, True)); End;
  """
        source = source.replace("Wait(0.050", extra + "Wait(0.050", 1)
        self.assertEqual(gate.validate_runtime(source), [])
        for native, invalid in (
            ("Ongoing - Global", "Ongoing - Globale"),
            ("For Global Variable", "For Globale Variable"),
            ("All Players", "Tutti Players"), ("All Teams", "Tutti Teams"),
            ("Is True For All", "Is True For Tutti"),
        ):
            with self.subTest(native=native):
                self.reject(source.replace(native, invalid, 1), "tradotto parzialmente")

    def test_partial_native_words_inside_strings_are_allowed(self):
        source = italian_minimal().replace('Custom String("OK")', 'Custom String("Ongoing - Globale; For Globale Variable; Tutti Teams")')
        self.assertEqual(gate.validate_runtime(source), [])

    def test_raw_unary_parentheses_fail_in_italian_and_english_values(self):
        for source, namespace in ((MINIMAL, 'Global.'), (italian_minimal(), 'Globale.')):
            for value in ('-(1)', '- (1)', '+(1)', 'Array(-(-1))', 'Vector(0, -(2), 0)'):
                with self.subTest(namespace=namespace, value=value):
                    broken = source.replace(namespace + 'PemainPemicu = Null;',
                                            namespace + 'PemainPemicu = ' + value + ';', 1)
                    self.reject(broken, 'segno unario')

    def test_native_signed_literals_binary_subtraction_and_quoted_signs_are_allowed(self):
        for value in ('-1', 'Array(-1, -0.500)', '(1 - (2 + 3))', 'Multiply(-1, (1 + 2))'):
            with self.subTest(value=value):
                source = MINIMAL.replace('Global.PemainAktif = Null;',
                                         'Global.AntreanPeristiwa = ' + value + ';\n  Global.PemainAktif = Null;', 1)
                self.assertEqual(gate.validate_runtime(source), [])
        source = MINIMAL.replace('Custom String("OK")', 'Custom String("= -(1); Vector(0, -(2), 0)")')
        self.assertEqual(gate.validate_runtime(source), [])


if __name__ == "__main__":
    unittest.main()
