from time import sleep

while True:
    print("\n=== System Admin Tools ===")
    print("1. Seed FULL System (Mongo + Neo4j + Influx)")
    print("2. Reset Entire System (DELETE ALL DATA)")
    print("3. Fetch / Print System Data Summary")
    print("4. Create Dean Account")
    print("5. Exit")

    choice = input("Enter your choice: ").strip()

    match choice:
        # =========================
        # FULL SYSTEM SEED
        # =========================
        case "1":
            from services.admin.system_full_seed import seed_entire_system
            seed_entire_system()

        # =========================
        # RESET SYSTEM
        # =========================
        case "2":
            confirm = input(
                "⚠️ This will DELETE ALL DATA. Type YES to confirm: "
            ).strip()

            if confirm == "YES":
                from services.admin.reset_system import reset_entire_system
                reset_entire_system()
            else:
                print("❌ Reset cancelled")

        # =========================
        # FETCH SUMMARY
        # =========================
        case "3":
            from services.admin.fetch_all_data import fetch_all_data_summary
            fetch_all_data_summary()

        # =========================
        # CREATE DEAN
        # =========================
        case "4":
            from services.admin.seed_dean import seed_dean_account
            seed_dean_account()

        # =========================
        # EXIT
        # =========================
        case "5":
            print("👋 Exiting Admin Tools...")
            sleep(1)
            break

        # =========================
        # INVALID
        # =========================
        case _:
            print("❗ Invalid choice, please try again.")
