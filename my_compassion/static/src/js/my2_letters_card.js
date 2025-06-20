/**
 * Owl component for displaying a letter card in the letters page.
 * The ideal would be to store the template in a separate file, but it
 * hadn't worked so far.
 */
odoo.define("my_compassion.OwlLetterCard", function (require) {
    "use strict";
    const { Component } = owl;
    const { xml } = owl.tags;

    class OwlLetterCard extends Component {
        static template = xml`
        <div class="letter-card">
            <t t-set="letter" t-value="props.letter"/>
            <link
                rel="stylesheet"
                href="/my_compassion/static/src/css/details_card.css"
            />
            <link
                rel="stylesheet"
                href="/my_compassion/static/src/css/letter_card.css"
            />
            <div class="details-card w-100"
            t-att-data-generator-id="letter.generator_id">
                <div class="details-card-body">
                    <div class="row align-items-center">
                        <!-- Left part of the card with the letter icon -->
                        <div class="col-5">
                            <div class="ml-3">
                                <i class="fa fa-envelope-o letter-icon"/>
                            </div>
                        </div>

                        <!-- Right part of the card component -->
                        <div class="col-7 h-100">
                            <div class="row">
                                <div class="col-12">
                                    <div
                                        class="text-right"
                                        t-att-data-direction="letter.direction or ''"
                                        t-att-data-scanned-date="letter.scanned_date or ''"
                                    >
                                        <p>
                                            <t t-esc="letter.scanned_date"/>
                                        </p>
                                        <p>
                                            <t t-esc="letter.direction"/>
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <!-- Buttons part -->
                            <div class="row">
                                <div class="offset-1 col-5">
                                    <a
                                        t-attf-href="/b2s_image?id={{letter.uuid}}&amp;disposition=inline&amp;file_type=pdf"
                                        target="_blank"
                                    >
                                        <button
                                            type="button"
                                            class="btn-compassion btn-compassion-blue"
                                        >
                                            <span>
                                                <i class="fa fa-eye"/>
                                            </span>
                                        </button>
                                    </a>
                                </div>
                                <div class="col-5 offset-1">
                                    <a
                                        t-attf-href="/b2s_image?id={{letter.uuid}}"
                                        t-attf-download="{{letter.name}}"
                                    >
                                        <button
                                            type="button"
                                            class="btn-compassion btn-compassion-blue"
                                        >
                                            <span>
                                                <i class="fa fa-download"/>
                                            </span>
                                        </button>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <script
                type="text/javascript"
                src="/my_compassion/static/src/js/my2_child_letters_highlight_new_letter.js"
            />

     </div>`; 
    }

    return OwlLetterCard;
});