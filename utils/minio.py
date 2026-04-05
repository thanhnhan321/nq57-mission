from django.core.files import File
from uuid import UUID

from minio import Minio
from minio.deleteobjects import DeleteObject

import env

minio_client = Minio(
    endpoint=env.MINIO_ENDPOINT,
    access_key=env.MINIO_ACCESS_KEY,
    secret_key=env.MINIO_SECRET_KEY,
    secure=False,
)

def upload(
    file: File,
    object_uid: UUID
):
    metadata = minio_client.put_object(
        bucket_name=env.MINIO_BUCKET,
        object_name=str(object_uid),
        data=file.file,
        length=file.size,
    )
    return metadata

def download(object_uid: UUID):
    return minio_client.get_object(env.MINIO_BUCKET, str(object_uid))

def delete(object_uids: list[UUID]):
    errors = minio_client.remove_objects(
        env.MINIO_BUCKET,
        [
            DeleteObject(str(object_uid))
            for object_uid in object_uids
        ]
    )
    return errors
