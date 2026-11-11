package br.com.finserve.aem.core.models;

import org.apache.sling.api.SlingHttpServletRequest;
import org.apache.sling.models.annotations.DefaultInjectionStrategy;
import org.apache.sling.models.annotations.Model;
import org.apache.sling.models.annotations.injectorspecific.ValueMapValue;
import javax.annotation.PostConstruct;

/** Reference Sling Model. Compile ONLY inside a real AEM Maven Archetype project with the AEM SDK API. */
@Model(
    adaptables = SlingHttpServletRequest.class,
    resourceType = "finserve/components/campaignhero",
    defaultInjectionStrategy = DefaultInjectionStrategy.OPTIONAL
)
public class CampaignHeroModel {
    @ValueMapValue private String eyebrow;
    @ValueMapValue private String title;
    @ValueMapValue private String description;
    @ValueMapValue private String ctaLabel;
    @ValueMapValue private String ctaUrl;
    @ValueMapValue private String segment;

    @PostConstruct
    protected void init() {
        if (title == null || title.isBlank()) title = "Planeje seu futuro com clareza";
        if (description == null) description = "Conteúdo demonstrativo";
        if (ctaLabel == null) ctaLabel = "Ver soluções";
        // Deliberately do not emit arbitrary external links from authored content.
        if (ctaUrl == null || !ctaUrl.startsWith("/") || ctaUrl.startsWith("//")) ctaUrl = "/content/finserve/br/pt.html";
        if (segment == null) segment = "all";
    }
    public String getEyebrow() { return eyebrow; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public String getCtaLabel() { return ctaLabel; }
    public String getCtaUrl() { return ctaUrl; }
    public String getSegment() { return segment; }
}
