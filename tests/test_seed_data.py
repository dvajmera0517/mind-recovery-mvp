from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mind_recovery_mvp.db import Base
from mind_recovery_mvp.loader import load_seed_data
from mind_recovery_mvp.models import NutrientContent
from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED


def test_seed_data_loads_all_records_including_nulls() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        load_seed_data(session)
        records = {
            record.medication_class: record
            for record in session.query(NutrientContent).all()
        }

    expected_classes = {record["medication_class"] for record in NUTRIENT_CONTENT_SEED}
    assert len(records) == len(NUTRIENT_CONTENT_SEED)
    assert set(records) == expected_classes

    for expected in NUTRIENT_CONTENT_SEED:
        actual = records[expected["medication_class"]]
        assert actual.content_status == expected["content_status"]
        assert actual.nutrient_concern == expected["nutrient_concern"]
        assert actual.why_it_matters == expected["why_it_matters"]
        assert actual.foods_that_may_help == expected["foods_that_may_help"]
        assert actual.supplements_to_discuss == expected["supplements_to_discuss"]
        assert actual.talk_to_pharmacist_if == expected["talk_to_pharmacist_if"]
        assert actual.clinical_source == expected["clinical_source"]
        assert actual.content_origin == expected["content_origin"]
