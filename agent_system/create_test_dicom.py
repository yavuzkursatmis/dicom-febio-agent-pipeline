from pathlib import Path
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, CTImageStorage, generate_uid
import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


out = Path(str(PROJECT_ROOT / 'user_data' / 'test_agent01_dicom' / 'test_ct.dcm'))

meta = Dataset()
meta.MediaStorageSOPClassUID = CTImageStorage
meta.MediaStorageSOPInstanceUID = generate_uid()
meta.TransferSyntaxUID = ExplicitVRLittleEndian
meta.ImplementationClassUID = generate_uid()

ds = FileDataset(str(out), {}, file_meta=meta, preamble=b"\0" * 128)
ds.Modality = "CT"
ds.SOPClassUID = CTImageStorage
ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
ds.StudyInstanceUID = generate_uid()
ds.SeriesInstanceUID = generate_uid()
ds.PatientID = "TEST"
ds.PatientName = "Anonymous^Test"
ds.StudyDate = datetime.date.today().strftime("%Y%m%d")
ds.Rows = 2
ds.Columns = 2
ds.PixelSpacing = [1.0, 1.0]
ds.SliceThickness = 1.0
ds.save_as(str(out))

print("Test DICOM oluşturuldu:", out)
