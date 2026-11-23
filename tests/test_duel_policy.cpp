#include "../src/PvPLifeDuelRequestPolicy.h"
#include "../src/PvPLifeDuelSelection.h"

#include <stdexcept>

namespace
{
    struct Candidate
    {
        std::uint32_t GuidLow;
        unsigned Level;
        unsigned Team;
        unsigned Phase;
    };

    void Expect(bool condition, char const* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }
}

int main()
{
    using PvPLife::DuelRequestAction;
    using PvPLife::EvaluateDuelRequest;

    Expect(EvaluateDuelRequest(false, false, false, false, false, 0, 0) == DuelRequestAction::Cast,
        "an idle pair may cast a request");
    Expect(EvaluateDuelRequest(true, false, false, false, false, 5, 6) == DuelRequestAction::Wait,
        "pending casts wait for state creation");
    Expect(EvaluateDuelRequest(true, true, false, false, false, 5, 6) == DuelRequestAction::Busy,
        "a different native duel is left alone");
    Expect(EvaluateDuelRequest(true, true, true, false, false, 5, 6) == DuelRequestAction::AcceptBot,
        "only the matching bot may accept while the request is open");
    Expect(EvaluateDuelRequest(true, true, true, true, false, 5, 6) == DuelRequestAction::Wait,
        "a real player controls invitation acceptance");
    Expect(EvaluateDuelRequest(true, true, true, true, false, 6, 6) == DuelRequestAction::TimedOut,
        "a matching but unanswered player invitation expires");
    Expect(EvaluateDuelRequest(true, true, true, false, false, 6, 6) == DuelRequestAction::TimedOut,
        "an overdue bot invitation may no longer be accepted");
    Expect(EvaluateDuelRequest(true, true, true, true, true, 6, 6) == DuelRequestAction::Confirmed,
        "a live countdown survives the invitation deadline");
    Expect(PvPLife::DuelApproachDistance(3.0f) == 2.0f, "approach respects shorter spell ranges");

    std::vector<Candidate> pool = {{1, 15, 0, 1}, {2, 17, 0, 1}, {3, 16, 1, 1}, {4, 80, 0, 1},
        {5, 80, 0, 1}, {6, 15, 0, 2}};
    auto [attackers, defenders] = PvPLife::SelectDiverseDuelPairs(pool, pool, 3, 5,
        [](Candidate const& a, Candidate const& b) { return (a.Phase & b.Phase) != 0; });
    Expect(attackers.size() == 2 && defenders.size() == 2, "isolated faction or phase is left unpaired");
    for (std::size_t index = 0; index < attackers.size(); ++index)
    {
        Expect(attackers[index].GuidLow != defenders[index].GuidLow, "a bot cannot duel itself");
        Expect(attackers[index].Team == defenders[index].Team, "faction filters are preserved");
        Expect((attackers[index].Phase & defenders[index].Phase) != 0, "incompatible phases are skipped");
        Expect(attackers[index].Level <= defenders[index].Level + 5 &&
            defenders[index].Level <= attackers[index].Level + 5, "level-gap filter is preserved");
    }
}
