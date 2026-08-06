from graph import graph


def run(title, inputs):
    print(f"\n===== {title} =====")
    st = {"step": "greet", "user_input": ""}
    st = graph.invoke(st)
    print("BOT:", st["reply"])
    for u in inputs:
        print("YOU:", u)
        st["user_input"] = u
        st = graph.invoke(st)
        print("BOT:", st["reply"])
        if st.get("done"):
            break
    print("FINAL:", {k: st.get(k) for k in
                     ("problem", "is_emergency", "address", "time_preference", "done")})


run("Emergency + INLINE time correction at confirm", [
    "it's 95 degrees, no AC, and my baby is home",
    "987 Oak Street",
    "tomorrow at 9pm",
    "actually make it 8pm",   # <-- inline correction; should update time and re-confirm
    "yes",
])

run("Routine, straight through", [
    "my AC is making a rattling noise",
    "45 Oak Avenue",
    "Saturday afternoon",
    "yes",
])
