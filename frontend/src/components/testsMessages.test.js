import assert from 'node:assert/strict'
import { test } from 'node:test'
import { NOT_PAID, listErrorMessage } from './testsMessages.js'

test('an unpaid student (403) is told to pay first, not that loading failed', () => {
  assert.equal(listErrorMessage(403), NOT_PAID)
  assert.match(NOT_PAID, /once your application fee has been paid/)
})

test('any other failure still asks the student to refresh', () => {
  for (const status of [500, 502, undefined]) {
    assert.equal(listErrorMessage(status), 'Could not load your aptitude tests. Try refreshing.')
  }
})
