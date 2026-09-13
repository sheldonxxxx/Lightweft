const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const order = photo => Number.isFinite(photo.metadata?.sequenceOrder) ? photo.metadata.sequenceOrder : Infinity;

export function sequenceForPhoto(dataset, photo) {
  const id = photo.metadata?.sequenceGroup;
  if (!nonempty(id)) return null;
  const cases = dataset.cases
    .map((item, index) => ({item, index}))
    .filter(({item}) => item.metadata?.sequenceGroup === id)
    .sort((a, b) => order(a.item) - order(b.item) || a.index - b.index)
    .map(({item}) => item);
  const labelled = cases.find(item => nonempty(item.metadata?.sequenceLabel));
  return {id, label: labelled?.metadata.sequenceLabel.trim() || id, cases};
}

export function sequenceComparison(sequence, leftId, rightId) {
  return sequence.cases.map(photo => ({photo,
    left: photo.variants.find(variant => variant.id === leftId) || null,
    right: photo.variants.find(variant => variant.id === rightId) || null}));
}

export function photoReviewURL(datasetId, caseId) {
  return `?${new URLSearchParams({dataset: datasetId, case: caseId, panel: 'review'})}`;
}
