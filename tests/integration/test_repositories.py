"""Integration tests for repository CRUD operations."""

from __future__ import annotations

from app.repositories import monster_repo, target_repo, settings_repo
from app.domain.models import MonsterType


class TestMonsterRepo:
    def test_fetch_all_monsters(self, content_conn):
        monsters = monster_repo.fetch_all_monsters(content_conn)
        assert len(monsters) == 7
        names = {m.name for m in monsters}
        assert "Zynth" in names
        assert "Galvana" in names

    def test_fetch_by_type(self, content_conn):
        wublins = monster_repo.fetch_monsters_by_type(content_conn, MonsterType.WUBLIN)
        assert len(wublins) == 3
        assert all(m.monster_type == MonsterType.WUBLIN for m in wublins)

    def test_fetch_egg_types_map(self, content_conn):
        emap = monster_repo.fetch_egg_types_map(content_conn)
        assert len(emap) == 15
        mammott = next(e for e in emap.values() if e.name == "Mammott")
        assert mammott.breeding_time_seconds == 1800

    def test_fetch_requirements(self, content_conn, id_maps):
        reqs = monster_repo.fetch_requirements_for_monster(content_conn, id_maps["monsters"]["Galvana"])
        assert len(reqs) == 4
        egg_ids = {r.egg_type_id for r in reqs}
        assert id_maps["eggs"]["Bowgart"] in egg_ids
        assert id_maps["eggs"]["Mammott"] in egg_ids

    def test_update_metadata(self, content_conn):
        meta = monster_repo.fetch_update_metadata(content_conn)
        assert meta["content_version"] == "0.1.0-dev"
        assert meta["source"] == "seed"


class TestTargetRepo:
    def test_insert_and_fetch(self, userstate_conn):
        tid = target_repo.insert_target(userstate_conn, monster_id=1)
        userstate_conn.commit()
        targets = target_repo.fetch_all_targets(userstate_conn)
        assert len(targets) == 1
        assert targets[0].id == tid
        assert targets[0].monster_id == 1

    def test_delete_target(self, userstate_conn):
        tid = target_repo.insert_target(userstate_conn, monster_id=1)
        userstate_conn.commit()
        target_repo.delete_target(userstate_conn, tid)
        userstate_conn.commit()
        assert target_repo.fetch_all_targets(userstate_conn) == []

    def test_newest_target_for_monster(self, userstate_conn):
        t1 = target_repo.insert_target(userstate_conn, monster_id=5)
        t2 = target_repo.insert_target(userstate_conn, monster_id=5)
        userstate_conn.commit()
        newest = target_repo.fetch_newest_target_for_monster(userstate_conn, 5)
        assert newest is not None
        assert newest.id == t2

    def test_progress_materialize_and_fetch(self, userstate_conn, content_conn, id_maps):
        from app.domain.models import MonsterRequirement
        tid = target_repo.insert_target(userstate_conn, monster_id=id_maps["monsters"]["Zynth"])
        reqs = monster_repo.fetch_requirements_for_monster(content_conn, id_maps["monsters"]["Zynth"])
        target_repo.materialize_progress(userstate_conn, tid, reqs)
        userstate_conn.commit()

        progress = target_repo.fetch_all_progress(userstate_conn)
        assert len(progress) == 4

    def test_increment_and_fetch(self, userstate_conn, content_conn, id_maps):
        tid = target_repo.insert_target(userstate_conn, monster_id=id_maps["monsters"]["Zynth"])
        reqs = monster_repo.fetch_requirements_for_monster(content_conn, id_maps["monsters"]["Zynth"])
        target_repo.materialize_progress(userstate_conn, tid, reqs)
        userstate_conn.commit()

        bowgart_id = id_maps["eggs"]["Bowgart"]
        new_val = target_repo.increment_progress(userstate_conn, tid, bowgart_id)
        userstate_conn.commit()
        assert new_val == 1


class TestSettingsRepo:
    def test_get_default(self, userstate_conn):
        val = settings_repo.get(userstate_conn, "nonexistent", "fallback")
        assert val == "fallback"

    def test_set_and_get(self, userstate_conn):
        settings_repo.set_value(userstate_conn, "breed_list_sort_order", "name_asc")
        assert settings_repo.get(userstate_conn, "breed_list_sort_order") == "name_asc"
