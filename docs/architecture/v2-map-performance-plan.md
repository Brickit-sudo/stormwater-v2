# V2 Map Performance Plan

## Scope

The V2 site map foundation lives at `/map`. It shows non-archived CRM sites that already have stored latitude and longitude values. This phase does not geocode, route crews, dispatch work, schedule visits, sync providers, or create reports.

## Lazy Frontend Boundary

- `apps/web/src/app/map/page.tsx` is the only route that imports the map component.
- `apps/web/src/components/map/SiteMap.tsx` is loaded through `next/dynamic` with `ssr: false`.
- Normal CRM pages, `AppShell`, and `Sidebar` do not import Leaflet or React Leaflet.
- The dashboard does not render the map by default.

## Map Library

The implementation uses Leaflet and React Leaflet because they add a no-key map foundation cleanly. Tiles use OpenStreetMap's public tile URL for local development; Google Maps, Mapbox, routing, geocoding, and paid/provider-key setup are deferred.

The marker strategy uses canvas-backed `CircleMarker` points instead of default image markers. That keeps the first version light, avoids marker asset work, and remains safe for the endpoint's capped result set.

## Backend Payload

`GET /v1/sites/map` returns lightweight location rows only:

- `id`
- `name`
- `client_id`
- `client_name`
- `status`
- `address`
- `city`
- `state`
- `latitude`
- `longitude`

The endpoint excludes archived sites and only returns sites with both latitude and longitude. It does not return notes, Drive metadata, linked file arrays, job arrays, report arrays, or full site payloads.

Supported query params:

- `organization_id` required
- `status` optional
- `client_id` optional
- `north`, `south`, `east`, `west` optional
- `limit` default `1000`, max `5000`
- `offset` default `0`

## No Render-Time Geocoding

Coordinates must already be stored on `sites.latitude` and `sites.longitude`. The map route never geocodes on render, never bulk geocodes, and never refreshes automatically. Users can manually use **Refresh Map** to re-fetch the lightweight endpoint.

## Deferred Work

Deferred until real product requirements exist:

- Google Maps or Mapbox provider setup
- production tile provider selection or local tile server
- routing and route optimization
- crew dispatch
- calendar scheduling from the map
- geocoding workflows
- report or photosheet generation from map selections
