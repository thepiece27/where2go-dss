from scripts.build_local_basemaps import classify_way, merge_render_features


def test_basemap_way_classification():
    assert classify_way({"highway": "primary"}) == ("road", "major", False)
    assert classify_way({"highway": "residential"}) == ("road", "local", False)
    assert classify_way({"highway": "service"}) is None
    assert classify_way({"highway": "service", "name": "Lối vào"}) == ("road", "local", False)
    assert classify_way({"natural": "water"}) == ("water", "area", True)
    assert classify_way({"building": "yes"}) is None


def test_merge_render_features_collapses_visual_classes():
    features = [
        {"properties": {"kind": "road", "class": "local", "name": "A"},
         "geometry": {"type": "LineString", "coordinates": [[105, 21], [106, 22]]}},
        {"properties": {"kind": "road", "class": "local", "name": "B"},
         "geometry": {"type": "MultiLineString", "coordinates": [[[106, 22], [107, 23]]]}},
        {"properties": {"kind": "water", "class": "area", "name": ""},
         "geometry": {"type": "Polygon", "coordinates": [[[105, 21], [106, 21], [106, 22], [105, 21]]]}},
    ]
    merged = merge_render_features(features)
    assert [(row["properties"]["kind"], row["geometry"]["type"]) for row in merged] == [
        ("water", "MultiPolygon"), ("road", "MultiLineString"),
    ]
    assert len(merged[1]["geometry"]["coordinates"]) == 2
