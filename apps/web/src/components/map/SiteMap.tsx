"use client";

import "leaflet/dist/leaflet.css";

import Link from "next/link";
import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { latLngBounds, type LatLngExpression, type PathOptions } from "leaflet";

import StatusBadge from "@/components/crm/StatusBadge";
import type { MapSite } from "@/lib/types";

import styles from "./SiteMap.module.css";

type SiteMapProps = {
  sites: MapSite[];
  selectedSiteId: string | null;
  onSelectSite: (site: MapSite) => void;
};

type MappableSite = MapSite & {
  latitudeValue: number;
  longitudeValue: number;
};

const DEFAULT_CENTER: LatLngExpression = [43.6591, -70.2568];
const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const statusPathOptions: Record<string, PathOptions> = {
  active: {
    color: "#45e04f",
    fillColor: "#45e04f",
    fillOpacity: 0.8,
    weight: 2,
  },
  on_hold: {
    color: "#f5d328",
    fillColor: "#f5d328",
    fillOpacity: 0.78,
    weight: 2,
  },
  inactive: {
    color: "#6f8583",
    fillColor: "#6f8583",
    fillOpacity: 0.7,
    weight: 2,
  },
};

const selectedPathOptions: PathOptions = {
  color: "#f4f7f2",
  fillColor: "#45e04f",
  fillOpacity: 0.95,
  weight: 3,
};

function parseSite(site: MapSite): MappableSite | null {
  const latitudeValue = Number(site.latitude);
  const longitudeValue = Number(site.longitude);
  if (!Number.isFinite(latitudeValue) || !Number.isFinite(longitudeValue)) {
    return null;
  }
  return { ...site, latitudeValue, longitudeValue };
}

function formatLocation(site: MapSite): string {
  return [site.city, site.state].filter(Boolean).join(", ") || "Location not set";
}

function siteHref(site: MapSite): string {
  const params = new URLSearchParams({
    client_id: site.client_id,
    site_id: site.id,
  });
  return `/crm/sites?${params.toString()}`;
}

function FitMapToSites({ sites }: { sites: MappableSite[] }) {
  const map = useMap();

  useEffect(() => {
    if (sites.length === 0) {
      map.setView(DEFAULT_CENTER, 8, { animate: false });
      return;
    }

    if (sites.length === 1) {
      map.setView([sites[0].latitudeValue, sites[0].longitudeValue], 12, {
        animate: false,
      });
      return;
    }

    const bounds = latLngBounds(
      sites.map(
        (site) => [site.latitudeValue, site.longitudeValue] as LatLngExpression,
      ),
    );
    map.fitBounds(bounds, {
      animate: false,
      maxZoom: 12,
      padding: [36, 36],
    });
  }, [map, sites]);

  return null;
}

function FlyToSelected({
  selectedSite,
}: {
  selectedSite: MappableSite | undefined;
}) {
  const map = useMap();

  useEffect(() => {
    if (!selectedSite) {
      return;
    }

    map.flyTo(
      [selectedSite.latitudeValue, selectedSite.longitudeValue],
      Math.max(map.getZoom(), 12),
      { duration: 0.45 },
    );
  }, [map, selectedSite]);

  return null;
}

export default function SiteMap({
  sites,
  selectedSiteId,
  onSelectSite,
}: SiteMapProps) {
  const mappableSites = useMemo(
    () => sites.map(parseSite).filter((site): site is MappableSite => site !== null),
    [sites],
  );
  const selectedSite = useMemo(
    () => mappableSites.find((site) => site.id === selectedSiteId),
    [mappableSites, selectedSiteId],
  );

  return (
    <div className={styles.mapRoot}>
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={8}
        minZoom={5}
        maxZoom={18}
        preferCanvas
        scrollWheelZoom
        className={styles.mapCanvas}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url={TILE_URL}
        />
        <FitMapToSites sites={mappableSites} />
        <FlyToSelected selectedSite={selectedSite} />

        {/* Canvas-backed circles keep the route responsive for the capped map result set. */}
        {mappableSites.map((site) => {
          const selected = site.id === selectedSiteId;
          const pathOptions = selected
            ? selectedPathOptions
            : statusPathOptions[site.status] ?? {
                color: "#6aa3ff",
                fillColor: "#6aa3ff",
                fillOpacity: 0.72,
                weight: 2,
              };

          return (
            <CircleMarker
              key={site.id}
              center={[site.latitudeValue, site.longitudeValue]}
              eventHandlers={{
                click: () => onSelectSite(site),
              }}
              pathOptions={pathOptions}
              radius={selected ? 9 : 7}
            >
              <Popup>
                <div className="space-y-3 p-3">
                  <div>
                    <p className="text-sm font-semibold text-text">{site.name}</p>
                    <p className="mt-1 text-xs text-text-muted">
                      {site.client_name ?? "Client not loaded"}
                    </p>
                  </div>
                  <div className="space-y-1 text-xs text-text-secondary">
                    <p>{formatLocation(site)}</p>
                    {site.address ? <p>{site.address}</p> : null}
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <StatusBadge status={site.status} />
                    <Link
                      className="text-xs font-semibold text-green hover:text-green-strong"
                      href={siteHref(site)}
                    >
                      Open Sites
                    </Link>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
