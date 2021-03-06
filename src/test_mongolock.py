from datetime import datetime
import pytest
from pymongo import MongoClient
from mongolock import MongoLock, MongoLockLocked, MongoLockException


connection = MongoClient()
db_name = 'mongolock_test'
col_name = 'locks'


@pytest.fixture()
def lock():
    connection[db_name][col_name].remove()
    return MongoLock(client=connection, db=db_name, collection=col_name)


def test_locked_successfully(lock):
    assert lock.lock('key', 'owner')


def test_locked_successfully_second_time(lock):
    lock.lock('key', 'owner')
    lock.release('key', 'owner')
    assert lock.lock('key', 'owner')


def test_lock_already_locked(lock):
    assert lock.lock('key', 'another_one')
    assert lock.lock('key', 'owner') is False


def test_lock_stealed(lock):
    lock.lock('key', 'owner', expire=0.1)
    assert lock.lock('key', 'owner', timeout=10)


def test_release(lock):
    lock.lock('key', 'owner')
    lock.release('key', 'owner')
    result = lock.get_lock_info('key')
    assert result['locked'] is False


def test_should_not_release_not_lock_owned_by_another_one(lock):
    lock.lock('key', 'another_one')
    assert lock.get_lock_info('key')['locked']


def test_should_not_release_not_locked_lock(lock):
    lock.release('key', 'owner')
    assert lock.get_lock_info('key') is None


def test_context(lock):
    current_lock = lock.get_lock_info('key')
    assert current_lock is None
    with lock('key', 'owner'):
        result = lock.get_lock_info('key')
        assert result['locked']


def test_context_raises_if_locked(lock):
    lock.lock('key', 'owner')
    with pytest.raises(MongoLockLocked):
        with lock('key', 'owner'):
            result = lock.get_lock_info('key')
            assert result['locked']


def test_touch(lock):
    dtnow = datetime.utcnow()
    lock.lock('key', 'owner', expire=1)
    lock.touch('key', 'owner')
    new_expire = lock.get_lock_info('key')['expire']
    assert new_expire > dtnow


def test_cant_touch_locked_by_another(lock):
    lock.lock('key', 'another_one', expire=1)
    with pytest.raises(MongoLockException):
        lock.touch('key', 'owner')


def touch_expired_not_specified(lock):
    lock.lock('key', 'owner', expire=1)
    lock.touch('key', 'owner')
    assert lock.get_lock_info('key')['expire'] is None


def test_create_lock_by_collection():
    connection[db_name][col_name].remove()
    collection = connection[db_name][col_name]
    assert MongoLock(collection=collection).lock('key', 'owner')
