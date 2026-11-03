SCREENS = {"platformer": "plataforma", "flight": "voo", "boss": "chefe"}


def resolve_choice(state, level, phases, choice):
    messages = state.messages
    item = level.item_for(state.phase_index, choice)
    if not level.is_correct(state.phase_index, choice):
        return {"correct": False, "item": item}

    state.phase_index += 1
    if state.phase_index >= len(phases):
        state.win()
        text = (
            messages["victory"] + "\n"
            + messages["voucher"] + "\n"
            + state.score_text()
        )
        return {
            "correct": True,
            "item": item,
            "text": text,
            "title": "Parabéns",
            "action": "hub",
        }

    following = phases[state.phase_index]
    text = messages["chest_correct"] + "\n" + item + "\n" + following.intro
    return {
        "correct": True,
        "item": item,
        "text": text,
        "title": following.name,
        "action": "go:" + SCREENS[following.kind],
    }