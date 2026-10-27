package main

import (
	"github.com/maxmind/mmdbwriter"
	"github.com/maxmind/mmdbwriter/mmdbtype"
	"log"
	"net"
	"os"
)

func main() {
	if len(os.Args) != 2 {
		log.Fatal("usage: generate-asn-fixture OUTPUT.mmdb (isolated tests only)")
	}
	w, e := mmdbwriter.New(mmdbwriter.Options{DatabaseType: "CyberPanel-ASN-QA", RecordSize: 24, IPVersion: 6})
	if e != nil {
		log.Fatal(e)
	}
	entries := map[string]uint32{"1.0.0.1/32": 64500, "1.128.0.1/32": 64502, "2001:1700::1/128": 64501, "2001:1c00::1/128": 64502, "88.252.206.167/32": 64502}
	for cidr, asn := range entries {
		_, n, e := net.ParseCIDR(cidr)
		if e != nil {
			log.Fatal(e)
		}
		e = w.Insert(n, mmdbtype.Map{"autonomous_system_number": mmdbtype.Uint32(asn), "autonomous_system_organization": mmdbtype.String("Synthetic CyberPanel isolated QA")})
		if e != nil {
			log.Fatal(e)
		}
	}
	f, e := os.Create(os.Args[1])
	if e != nil {
		log.Fatal(e)
	}
	defer f.Close()
	if _, e = w.WriteTo(f); e != nil {
		log.Fatal(e)
	}
}
