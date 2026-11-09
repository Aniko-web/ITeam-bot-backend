import asyncio
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.scrim import Scrim, ScrimReadyCheck
from app.models.pvp import PvPLobby, PvPParticipant
from app.models.karma import KarmaLog

DEMO_USERS = [
    {
        "telegram_id": 101,
        "username": "viper_king",
        "first_name": "Sardor",
        "in_game_nickname": "ViperKing",
        "mlbb_id": "78491032",
        "server_id": "2048",
        "current_rank": "Mythic Immortal",
        "highest_rank": "Mythic Immortal",
        "current_stars": 115,
        "main_roles": ["Jungler", "Mid Laner"],
        "top_heroes": ["Ling", "Fanny", "Hayabusa"],
        "playtime_schedule": "20:00 - 01:00 UTC+5",
        "karma_score": 145,
    },
    {
        "telegram_id": 102,
        "username": "aura_roam",
        "first_name": "Aziz",
        "in_game_nickname": "AuraRoam",
        "mlbb_id": "89201923",
        "server_id": "1002",
        "current_rank": "Mythic Immortal",
        "highest_rank": "Mythic Immortal",
        "current_stars": 102,
        "main_roles": ["Roamer"],
        "top_heroes": ["Chou", "Tigreal", "Franco"],
        "playtime_schedule": "20:00 - 00:00 UTC+5",
        "karma_score": 140,
    },
    {
        "telegram_id": 103,
        "username": "gold_rush",
        "first_name": "Jasur",
        "in_game_nickname": "GoldRush",
        "mlbb_id": "44291038",
        "server_id": "3021",
        "current_rank": "Mythic Glory",
        "highest_rank": "Mythic Glory",
        "current_stars": 65,
        "main_roles": ["Gold Laner"],
        "top_heroes": ["Claude", "Beatrix", "Brody"],
        "playtime_schedule": "19:00 - 23:00 UTC+5",
        "karma_score": 112,
    },
    {
        "telegram_id": 104,
        "username": "mage_supreme",
        "first_name": "Temur",
        "in_game_nickname": "MageSupreme",
        "mlbb_id": "90218392",
        "server_id": "2048",
        "current_rank": "Mythic Honor",
        "highest_rank": "Mythic Honor",
        "current_stars": 35,
        "main_roles": ["Mid Laner"],
        "top_heroes": ["Valentina", "Pharsa", "Novaria"],
        "playtime_schedule": "21:00 - 01:00 UTC+5",
        "karma_score": 98,
    },
    {
        "telegram_id": 105,
        "username": "iron_wall",
        "first_name": "Bobur",
        "in_game_nickname": "IronWall",
        "mlbb_id": "67182910",
        "server_id": "1002",
        "current_rank": "Mythic Glory",
        "highest_rank": "Mythic Glory",
        "current_stars": 58,
        "main_roles": ["Exp Laner"],
        "top_heroes": ["Yu Zhong", "Terizla", "Paquito"],
        "playtime_schedule": "20:00 - 00:00 UTC+5",
        "karma_score": 108,
    },
    {
        "telegram_id": 106,
        "username": "shadow_ace",
        "first_name": "Farrukh",
        "in_game_nickname": "ShadowAce",
        "mlbb_id": "11928301",
        "server_id": "2048",
        "current_rank": "Mythic Immortal",
        "highest_rank": "Mythic Immortal",
        "current_stars": 120,
        "main_roles": ["Jungler", "Exp Laner"],
        "top_heroes": ["Martis", "Helcurd", "Chou"],
        "playtime_schedule": "21:00 - 02:00 UTC+5",
        "karma_score": 130,
    },
    {
        "telegram_id": 107,
        "username": "night_stalker",
        "first_name": "Davron",
        "in_game_nickname": "NightStalker",
        "mlbb_id": "33918273",
        "server_id": "3021",
        "current_rank": "Mythic Glory",
        "highest_rank": "Mythic Glory",
        "current_stars": 70,
        "main_roles": ["Exp Laner"],
        "top_heroes": ["Balmond", "Gatotkaca", "Zilong"],
        "playtime_schedule": "20:00 - 00:00 UTC+5",
        "karma_score": 115,
    },
    {
        "telegram_id": 108,
        "username": "phantom_mid",
        "first_name": "Sherzod",
        "in_game_nickname": "PhantomMid",
        "mlbb_id": "88271039",
        "server_id": "1002",
        "current_rank": "Mythic Honor",
        "highest_rank": "Mythic Glory",
        "current_stars": 42,
        "main_roles": ["Mid Laner"],
        "top_heroes": ["Valentina", "Harith", "Nana"],
        "playtime_schedule": "19:00 - 23:30 UTC+5",
        "karma_score": 102,
    },
    {
        "telegram_id": 109,
        "username": "silent_roam",
        "first_name": "Otabek",
        "in_game_nickname": "SilentRoam",
        "mlbb_id": "55192837",
        "server_id": "2048",
        "current_rank": "Mythic",
        "highest_rank": "Mythic Honor",
        "current_stars": 24,
        "main_roles": ["Roamer"],
        "top_heroes": ["Grock", "Baxia", "Mathilda"],
        "playtime_schedule": "20:00 - 00:00 UTC+5",
        "karma_score": 92,
    },
    {
        "telegram_id": 110,
        "username": "dark_gold",
        "first_name": "Umid",
        "in_game_nickname": "DarkGold",
        "mlbb_id": "77281903",
        "server_id": "1002",
        "current_rank": "Mythic Glory",
        "highest_rank": "Mythic Glory",
        "current_stars": 55,
        "main_roles": ["Gold Laner"],
        "top_heroes": ["Irithel", "Bruno", "Karrie"],
        "playtime_schedule": "20:30 - 01:00 UTC+5",
        "karma_score": 96,
    },
]

async def seed_database():
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        print("Seeding Users...")
        for u_data in DEMO_USERS:
            user = await db.get(User, u_data["telegram_id"])
            if not user:
                user = User(
                    telegram_id=u_data["telegram_id"],
                    username=u_data["username"],
                    first_name=u_data["first_name"],
                    in_game_nickname=u_data["in_game_nickname"],
                    mlbb_id=u_data["mlbb_id"],
                    server_id=u_data["server_id"],
                    current_rank=u_data["current_rank"],
                    highest_rank=u_data["highest_rank"],
                    current_stars=u_data["current_stars"],
                    main_roles=u_data["main_roles"],
                    top_heroes=u_data["top_heroes"],
                    playtime_schedule=u_data["playtime_schedule"],
                    karma_score=u_data["karma_score"],
                    istars_balance=250,
                    selected_background_id="deep-void",
                    is_lfg_active=True,
                    total_scrims_played=15,
                    total_pvp_played=12
                )
                db.add(user)
        await db.commit()

        # Seed Teams
        print("Seeding Competitive Teams...")
        team1 = Team(
            id="team-apex-001",
            captain_id=101,
            name="Apex Legends Uzbekistan",
            tag="APEX",
            description="Tier 1 competitive squad preparing for regional qualifier tournaments.",
            voice_type="discord",
            voice_link_secret="https://discord.gg/apex-pro-scrims",
            max_slots=7,
            is_recruiting=True,
            min_rank_requirement="Mythic Glory"
        )
        team2 = Team(
            id="team-shdw-002",
            captain_id=106,
            name="Shadow Syndicate",
            tag="SHDW",
            description="Fast paced aggressive draft roster. Seeking flex Gold laner.",
            voice_type="telegram_voice",
            voice_link_secret="https://t.me/+shdw_voice_private",
            max_slots=7,
            is_recruiting=True,
            min_rank_requirement="Mythic"
        )

        db.add(team1)
        db.add(team2)
        await db.flush()

        # Team 1 Members
        t1_members = [
            (101, "captain", "Jungler", "active"),
            (102, "starter", "Roamer", "active"),
            (103, "starter", "Gold Laner", "active"),
            (104, "starter", "Mid Laner", "active"),
            (105, "starter", "Exp Laner", "active"),
        ]
        for uid, stype, role, status in t1_members:
            db.add(TeamMember(team_id=team1.id, user_id=uid, slot_type=stype, assigned_role=role, status=status))

        # Team 2 Members
        t2_members = [
            (106, "captain", "Jungler", "active"),
            (107, "starter", "Exp Laner", "active"),
            (108, "starter", "Mid Laner", "active"),
            (109, "starter", "Roamer", "active"),
            (110, "starter", "Gold Laner", "active"),
        ]
        for uid, stype, role, status in t2_members:
            db.add(TeamMember(team_id=team2.id, user_id=uid, slot_type=stype, assigned_role=role, status=status))

        await db.commit()

        # Seed Scrim
        print("Seeding Live Scrim & Ready Checks...")
        now = datetime.utcnow()
        scrim = Scrim(
            id="scrim-live-001",
            host_team_id=team1.id,
            challenger_team_id=team2.id,
            target_time=now + timedelta(minutes=8),
            target_rank="Mythic Glory",
            format="BO3",
            status="ready_check_pending",
            ready_check_started_at=now,
            ready_check_deadline=now + timedelta(minutes=5),
            custom_room_id="940128",
            custom_room_password="777",
            notes="Tournament draft rules. 5m ready check."
        )
        db.add(scrim)
        await db.flush()

        # 8 confirmed, 2 waiting
        all_10 = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        for i, uid in enumerate(all_10):
            tid = team1.id if i < 5 else team2.id
            is_r = i < 8  # first 8 ready, last 2 pending
            db.add(ScrimReadyCheck(
                scrim_id=scrim.id,
                user_id=uid,
                team_id=tid,
                is_ready=is_r,
                confirmed_at=now if is_r else None,
                expires_at=now + timedelta(minutes=5)
            ))

        # Seed PvP Lobby
        print("Seeding Community 5v5 PvP Lobby...")
        lobby = PvPLobby(
            id="lobby-e8a1b2",
            lobby_code="E8A1B2",
            title="Uzbekistan Community 5v5 Custom",
            creator_telegram_id=101,
            format="BO1",
            target_rank="Mythic",
            max_slots=10,
            status="open",
            custom_room_id="774910",
            custom_room_password="888"
        )
        db.add(lobby)
        await db.flush()

        # Add initial participants
        p_blue = [
            (101, 0, "BLUE", "Jungler"),
            (102, 1, "BLUE", "Roamer"),
            (103, 2, "BLUE", "Mid Laner"),
        ]
        p_red = [
            (106, 5, "RED", "Exp Laner"),
            (107, 6, "RED", "Gold Laner"),
        ]
        for uid, slot, side, role in p_blue + p_red:
            db.add(PvPParticipant(
                lobby_id=lobby.id,
                user_id=uid,
                slot_index=slot,
                team_side=side,
                selected_role=role,
                is_ready=True
            ))

        await db.commit()
        print("Database seeded successfully with demo esports players, rosters, scrims, and PvP lobby!")

if __name__ == "__main__":
    asyncio.run(seed_database())

