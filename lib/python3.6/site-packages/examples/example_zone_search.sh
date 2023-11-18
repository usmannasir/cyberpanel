:

ZONE=${1-example.com}
EXTRA=${2}

SEARCH_TYPES="
	equal
	not_equal
	greater_than
	less_than
	starts_with
	ends_with
	contains
	starts_with_case_sensitive
	ends_with_case_sensitive
	contains_case_sensitive
	list_contains
"

for search_type in ${SEARCH_TYPES}
do
	echo TRY: "name=${search_type}:${ZONE}"
	cli4 per_page=50 name="${search_type}:${ZONE}" ${EXTRA} /zones/ | jq -r '.[]|.id,.name' | paste - -
done

exit 0

