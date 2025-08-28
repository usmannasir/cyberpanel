:

#
# Show usage of GraphQL - see https://developers.cloudflare.com/analytics/graphql-api for all info
#

# pass one argument - the zone
ZONEID=`cli4 name="$1"  /zones | jq -r '.[].id'`
if [ "${ZONEID}" = "" ]
then
	echo "$1: zone not found" 1>&2
	exit 1
fi

# Just query the last 24 hours
DATE_BEFORE=`date -u +%Y-%m-%dT%H:%M:%SZ`
DATE_AFTER=`date -u -v -24H +%Y-%m-%dT%H:%M:%SZ`

# build the GraphQL query - this is just a simple example
QUERY='
  query {
    viewer {
      zones(filter: {zoneTag: "'${ZONEID}'"} ) {
        httpRequests1hGroups(limit:100, orderBy:[datetime_ASC], filter:{datetime_gt:"'${DATE_AFTER}'", datetime_lt:"'${DATE_BEFORE}'"}) {
          dimensions { datetime }
          sum { bytes }
        }
      }
    }
  }
'

# this not only does the query; but also drills down into the results to print the final data
cli4 --post query="${QUERY}" /graphql | jq -cr '.data.viewer.zones[]|.httpRequests1hGroups[]|.dimensions.datetime,.sum.bytes' | paste - - 
