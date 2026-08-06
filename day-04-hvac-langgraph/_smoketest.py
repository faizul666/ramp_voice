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


run("Emergency + loop-back (change time)", [
    "My heat is out and it's freezing in here",
    "123 Main Street",
    "tonight around 9",
    "actually, can you change it to tomorrow morning instead",
    "tomorrow morning at 8",
    "yes please",
])

run("Routine, straight through", [
    "My AC is making a rattling noise",
    "45 Oak Avenue",
    "Saturday afternoon",
    "yes",
])
