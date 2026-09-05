from pathlib import Path

import sca
from sca.config import DATA_ROOT, Config


def test_runtime_state_is_outside_installed_package():
    package_dir = Path(sca.__file__).resolve().parent
    roots = {
        Path(Config.UPLOAD_FOLDER).parent,
        Path(Config.DRAFT_FOLDER).parent,
        Path(Config.EXPORT_FOLDER).parent,
        Path(Config.SESSION_FILE_DIR).parent,
    }
    assert roots == {DATA_ROOT}
    assert DATA_ROOT != package_dir
    assert package_dir not in DATA_ROOT.parents
