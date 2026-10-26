import assert from 'node:assert/strict'
import { test } from 'node:test'
import { orderedRows } from './fieldLabels.js'

test('rows follow the form order, not the alphabet the database returns', () => {
  const saved = { religion: 'Hindu', mother_name: 'L', father_name: 'R', full_name: 'K', ews: false }
  assert.deepEqual(orderedRows(1, saved), [
    ['Full name', 'K'], ["Father's name", 'R'], ["Mother's name", 'L'], ['Religion', 'Hindu'], ['EWS', false],
  ])
})

test('the same key gets its own step label', () => {
  assert.deepEqual(orderedRows(4, { score: '8.1' }), [['UG score', '8.1']])
  assert.deepEqual(orderedRows(5, { score: '95' }), [['Score', '95']])
})

test('an unknown field still shows, last; storage keys never do', () => {
  const rows = orderedRows(6, { photo_url: 'applications/1/p.png', new_thing: 'x', id_proof_type: 'PAN' })
  assert.deepEqual(rows, [['ID proof type', 'PAN'], ['New thing', 'x']])
})

test('Class XII comes before Class X, labelled in words', () => {
  const labels = orderedRows(4, { x_board: 'CBSE', xii_board: 'State', x_year: '2022' }).map(([l]) => l)
  assert.deepEqual(labels, ['Class XII board', 'Class X board', 'Class X year of passing'])
})
