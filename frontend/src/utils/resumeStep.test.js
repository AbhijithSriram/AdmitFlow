import assert from 'node:assert/strict'
import { test } from 'node:test'
import { resumeStep } from './resumeStep.js'

const DOCS = { photo_url: 'p', signature_url: 's', id_proof_url: 'i', id_proof_type: 'Aadhaar' }

test('a finished form resumes at the preview, not the uploads step', () => {
  assert.equal(resumeStep(6, { 6: DOCS }), 7)
})

test('a half-done uploads step resumes on the uploads step', () => {
  assert.equal(resumeStep(6, { 6: { ...DOCS, signature_url: null } }), 6)
  assert.equal(resumeStep(6, {}), 6)
})

test('an earlier step resumes where the student stopped', () => {
  assert.equal(resumeStep(3, { 6: DOCS }), 3)
  assert.equal(resumeStep(0, {}), 1)
})
