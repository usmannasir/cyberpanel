:

ZONE=${1-example.com}

URL_MATCH="*.${ZONE}/url1*"
URL_FORWARDED="http://${ZONE}/url2"

cli4 --post \
	targets='[ { "target": "url", "constraint": { "operator": "matches", "value": "'${URL_MATCH}'" } } ]' \
	actions='[ { "id": "forwarding_url", "value": { "status_code": 302, "url": "'${URL_FORWARDED}'" } } ]' \
	status=active \
	priority=1 \
		/zones/:${ZONE}/pagerules | jq '{"status":.status,"priority":.priority,"id":.id}'

exit 0

