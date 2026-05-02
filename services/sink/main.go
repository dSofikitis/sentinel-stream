package main

import "fmt"

// Version is bumped per release; the real sink implementation lands
// in phase 7 (Redpanda -> ClickHouse batch insert).
const Version = "0.1.0"

func main() {
	fmt.Printf("sentinel-sink %s: scaffolded; implementation lands in phase 7.\n", Version)
}
